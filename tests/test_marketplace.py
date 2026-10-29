import unittest
from app import create_app
from extensions import db
from models import Product, Order

class MarketplaceTest(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///:memory:'})
        self.ctx=self.app.app_context();self.ctx.push();db.create_all();self.c=self.app.test_client()
        f=self.c.post('/api/farmers/signup',json={'name':'Test Farmer','phone':'9000000000','village':'Tandur'}).get_json()
        self.h={'Authorization':'Bearer '+f['api_key']}
        self.pid=self.c.post('/api/products',headers=self.h,json={'name':'Tomatoes','price':30.25,'quantity':10}).get_json()['id']
        self.payload={'customer_name':'Buyer','customer_phone':'9000000010','delivery_location':'Demo address','items':[{'product_id':self.pid,'quantity':2}]}
    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()
    def test_full_order_flow(self):
        r=self.c.post('/api/orders/create',json=self.payload);self.assertEqual(r.status_code,201)
        receipt=r.get_json();oid=receipt['order']['id'];h={'X-Order-Token':receipt['order_token']}
        self.assertEqual(receipt['order']['total_amount'],60.50)
        self.assertEqual(db.session.get(Product,self.pid).quantity,8)
        self.assertEqual(self.c.get(f'/api/orders/{oid}').status_code,403)
        self.assertEqual(self.c.get(f'/api/orders/{oid}',headers=h).status_code,200)
        self.assertEqual(self.c.post('/api/ratings',headers=h,json={'order_id':oid,'rating':5}).status_code,409)
        for status in ['confirmed','packed','in_transit','delivered']:
            self.assertEqual(self.c.put(f'/api/orders/{oid}/status',headers=self.h,json={'status':status}).status_code,200)
        self.assertEqual(self.c.post('/api/ratings',headers=h,json={'order_id':oid,'rating':5,'review_text':'Fresh!'}).status_code,201)
        self.assertEqual(self.c.post('/api/ratings',headers=h,json={'order_id':oid,'rating':5}).status_code,409)
    def test_stock_rollback(self):
        self.payload['items'][0]['quantity']=11
        self.assertEqual(self.c.post('/api/orders/create',json=self.payload).status_code,409)
        self.assertEqual(db.session.get(Product,self.pid).quantity,10);self.assertEqual(Order.query.count(),0)
    def test_validation(self):
        self.assertEqual(self.c.post('/api/products',json={}).status_code,401)
        self.assertEqual(self.c.get('/api/orders').status_code,401)
        for price in [-1,0,'NaN','Infinity',1.234]:
            self.assertEqual(self.c.post('/api/products',headers=self.h,json={'name':'Bad','price':price,'quantity':1}).status_code,400)
        self.assertEqual(self.c.post('/api/orders/create',json=[]).status_code,400)
        self.assertEqual(self.c.post('/api/farmers/signup',json={'name':'Other','phone':'9000000000','village':'X'}).status_code,409)
    def test_duplicate_items(self):
        self.payload['items']=[{'product_id':self.pid,'quantity':6},{'product_id':self.pid,'quantity':6}]
        self.assertEqual(self.c.post('/api/orders/create',json=self.payload).status_code,409)
        self.assertEqual(db.session.get(Product,self.pid).quantity,10)
    def test_farmer_isolation(self):
        f=self.c.post('/api/farmers/signup',json={'name':'Other','phone':'9000000002','village':'X'}).get_json();h={'Authorization':'Bearer '+f['api_key']}
        self.assertEqual(self.c.put(f'/api/products/{self.pid}',headers=h,json={'name':'Stolen','price':1,'quantity':1}).status_code,403)
        self.c.post('/api/orders/create',json=self.payload)
        self.assertEqual(self.c.get('/api/orders',headers=h).get_json(),[])
    def test_decline_restores_stock_once(self):
        oid=self.c.post('/api/orders/create',json=self.payload).get_json()['order']['id']
        self.assertEqual(self.c.put(f'/api/orders/{oid}/status',headers=self.h,json={'status':'declined'}).status_code,200)
        self.assertEqual(self.c.put(f'/api/orders/{oid}/status',headers=self.h,json={'status':'declined'}).status_code,400)
        self.assertEqual(db.session.get(Product,self.pid).quantity,10)
    def test_archive_preserves_order(self):
        r=self.c.post('/api/orders/create',json=self.payload).get_json()
        self.assertEqual(self.c.delete(f'/api/products/{self.pid}',headers=self.h).status_code,204)
        self.assertEqual(self.c.get('/api/products').get_json(),[])
        self.assertEqual(self.c.post('/api/orders/create',json=self.payload).status_code,409)
        self.assertEqual(self.c.get('/api/orders/'+str(r['order']['id']),headers={'X-Order-Token':r['order_token']}).status_code,200)

if __name__=='__main__':unittest.main()
