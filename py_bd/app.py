from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config_db import SQLALCHEMY_DATABASE_URI
import datetime
import os

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)
# ========================================
# ROUTES FRONTEND
# ========================================
@app.route('/')
@app.route('/connexion')
def index():
    return app.send_static_file('connexion.html')

@app.route('/inscription')
def inscription_page():
    return app.send_static_file('inscription.html')

@app.route('/patrimoine')
def patrimoine_page():
    return app.send_static_file('patrimoine.html')

# ========================================
# MODÈLES DE DONNÉES
# ========================================

class User(db.Model):
    __tablename__ = 'utilisateurs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'city': self.city,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Heritage(db.Model):
    __tablename__ = 'patrimoines'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'city': self.city,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# ========================================
# ROUTES AUTHENTIFICATION
# ========================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Données manquantes'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Cet email est déjà utilisé'}), 400
    
    new_user = User(
        name=data['name'],
        email=data['email'],
        password=data['password'],
        city=data.get('city')
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Inscription réussie',
        'user': new_user.to_dict()
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email et mot de passe requis'}), 400
    
    user = User.query.filter_by(email=data['email'], password=data['password']).first()
    if not user:
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
    
    return jsonify({
        'message': 'Connexion réussie',
        'user': user.to_dict()
    })

# ========================================
# ROUTES UTILISATEURS (CRUD)
# ========================================

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    
    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        # Vérifier si l'email est déjà pris par un autre utilisateur
        existing = User.query.filter(User.email == data['email'], User.id != user_id).first()
        if existing:
            return jsonify({'error': 'Cet email est déjà utilisé'}), 400
        user.email = data['email']
    if 'city' in data:
        user.city = data['city']
    if 'password' in data and data['password']:
        user.password = data['password']
        
    db.session.commit()
    return jsonify({'message': 'Utilisateur mis à jour', 'user': user.to_dict()})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Supprimer les patrimoines associés d'abord (ou laisser MySQL gérer via CASCADE)
    Heritage.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Utilisateur supprimé avec succès'})

# ========================================
# ROUTES PATRIMOINES (CRUD)
# ========================================

@app.route('/api/heritages', methods=['GET'])
def get_heritages():
    user_id = request.args.get('user_id')
    if user_id:
        heritages = Heritage.query.filter_by(user_id=user_id).all()
    else:
        heritages = Heritage.query.all()
    return jsonify({'heritages': [h.to_dict() for h in heritages]})

@app.route('/api/heritages', methods=['POST'])
def add_heritage():
    data = request.json
    try:
        new_heritage = Heritage(
            name=data['name'],
            description=data['description'],
            category=data['category'],
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            city=data.get('city'),
            user_id=data['userId']
        )
        db.session.add(new_heritage)
        db.session.commit()
        return jsonify({'message': 'Patrimoine ajouté', 'heritage': new_heritage.to_dict()}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/heritages/<int:heritage_id>', methods=['PUT'])
def update_heritage(heritage_id):
    heritage = Heritage.query.get_or_404(heritage_id)
    data = request.json
    try:
        heritage.name = data.get('name', heritage.name)
        heritage.description = data.get('description', heritage.description)
        heritage.category = data.get('category', heritage.category)
        heritage.latitude = float(data.get('latitude', heritage.latitude))
        heritage.longitude = float(data.get('longitude', heritage.longitude))
        heritage.city = data.get('city', heritage.city)
        
        db.session.commit()
        return jsonify({'message': 'Patrimoine mis à jour', 'heritage': heritage.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/heritages/<int:heritage_id>', methods=['DELETE'])
def delete_heritage(heritage_id):
    heritage = Heritage.query.get_or_404(heritage_id)
    db.session.delete(heritage)
    db.session.commit()
    return jsonify({'message': 'Patrimoine supprimé'})

if __name__ == '__main__':
    with app.app_context():
        # Tentative de création des tables
        try:
            db.create_all()
            print("Base de données initialisée (MySQL)")
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la base de données : {e}")
            print("Assurez-vous que MySQL est lancé et que la base 'patrimoine_db' existe.")
            
    app.run(debug=True, port=5000)
