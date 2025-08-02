from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# Configuration
DATABASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'arbitrage.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/opportunities')
def get_opportunities():
    min_profit = request.args.get('min_profit', 20, type=float)
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ao.*, p.title, p.url as source_url, p.price as source_price
        FROM arbitrage_opportunities ao
        JOIN products p ON ao.source_product_id = p.id
        WHERE ao.is_active = 1 AND ao.profit_margin >= ?
        ORDER BY ao.roi DESC, ao.profit_margin DESC
        LIMIT ?
    ''', (min_profit, limit))
    
    opportunities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(opportunities)

@app.route('/api/orders')
def get_orders():
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT o.*, p.title as product_title
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        ORDER BY o.created_at DESC
        LIMIT ?
    ''', (limit,))
    
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(orders)

@app.route('/api/metrics')
def get_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as active_listings FROM listings WHERE status = 'active'")
    active_listings = cursor.fetchone()['active_listings']
    
    cursor.execute('''
        SELECT COALESCE(SUM(sale_price - (SELECT price FROM products WHERE id = product_id) - fees), 0) as total_profit
        FROM sales_history
        WHERE strftime('%Y-%m', sale_date) = strftime('%Y-%m', 'now')
    ''')
    monthly_profit = cursor.fetchone()['total_profit']
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'active_listings': active_listings,
        'monthly_profit': monthly_profit
    })

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    
    # Create simple HTML template
    with open('templates/index.html', 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SuperArb Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100">
            <div class="container mx-auto p-4">
                <h1 class="text-2xl font-bold mb-4">SuperArb Dashboard</h1>
                <div id="metrics" class="grid grid-cols-2 gap-4 mb-6">
                    <!-- Metrics will be loaded here -->
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div class="bg-white p-4 rounded shadow">
                        <h2 class="text-xl font-semibold mb-2">Top Opportunities</h2>
                        <div id="opportunities">Loading...</div>
                    </div>
                    <div class="bg-white p-4 rounded shadow">
                        <h2 class="text-xl font-semibold mb-2">Recent Orders</h2>
                        <div id="orders">Loading...</div>
                    </div>
                </div>
            </div>
            <script>
                // Load data when page loads
                Promise.all([
                    fetch('/api/metrics').then(r => r.json()),
                    fetch('/api/opportunities?limit=5').then(r => r.json()),
                    fetch('/api/orders?limit=5').then(r => r.json())
                ]).then(([metrics, opportunities, orders]) => {
                    // Update metrics
                    document.getElementById('metrics').innerHTML = `
                        <div class="bg-white p-4 rounded shadow">
                            <div class="text-gray-500">Active Listings</div>
                            <div class="text-2xl font-bold">${metrics.active_listings}</div>
                        </div>
                        <div class="bg-white p-4 rounded shadow">
                            <div class="text-gray-500">Monthly Profit</div>
                            <div class="text-2xl font-bold">$${metrics.monthly_profit.toFixed(2)}</div>
                        </div>
                    `;
                    
                    // Update opportunities
                    document.getElementById('opportunities').innerHTML = 
                        opportunities.map(o => `
                            <div class="border-b py-2">
                                <div class="font-medium">${o.title}</div>
                                <div class="text-sm text-gray-600">
                                    Profit: $${o.estimated_profit.toFixed(2)} (${o.profit_margin.toFixed(1)}%)
                                </div>
                            </div>
                        `).join('') || 'No opportunities found';
                    
                    // Update orders
                    document.getElementById('orders').innerHTML = 
                        orders.map(o => `
                            <div class="border-b py-2">
                                <div class="font-medium">${o.product_title || 'Order ID: ' + o.id}</div>
                                <div class="text-sm text-gray-600">
                                    $${o.total_amount?.toFixed(2) || '0.00'} • ${o.status}
                                </div>
                            </div>
                        `).join('') || 'No orders found';
                });
            </script>
        </body>
        </html>
        ''')
    
    app.run(debug=True, port=5000)
