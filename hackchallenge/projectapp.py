#app.py

import json
import os
from projectdb import db, DiningHall, User, Swipe, MenuItem, Menu
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from collections import defaultdict


db_filename = "todo.db"
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_filename}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["PLATE_UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["PLATE_UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/api/users', methods=['GET'])
def get_users(): #✅
    users = []
    for user in User.query.all():
        users.append(user.serialize())
    return jsonify(users), 200

@app.route('/api/users/register', methods=['POST'])
def register_user(): #✅
    """
    Register a new user
    """
    data = request.get_json()
    username = data.get('username')
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"error": "Missing input fields"}), 400
    
    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({"error": "Username or email already exists"}), 400
    
    user = User(
        username=username,
        name=name,
        email=email,
        passwordHash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(user.serialize()), 201

@app.route('/api/users/login', methods=['POST'])
def login_user(): #✅
    """
    Login a user
    """

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user= User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.passwordHash, password):
        return jsonify({"error": "Invalid username or password"}), 401
    return jsonify(user.serialize()),200

@app.route('/api/dininghalls', methods=['GET'])
def get_dining_halls(): #✅
    """
    Get all dining halls
    """
    dining_halls = []
    for dining_hall in DiningHall.query.all():
        dining_halls.append(dining_hall.serialize())
    return jsonify(dining_halls), 200

# @app.route('/api/users/<int:user_id>', methods=['DELETE']) # new method C R U D-Delete
# def delete_user_account(user_id):  #✅
#     """
#     Delete a user account
#     """
#     user = User.query.get(user_id)
#     if user is None:
#         return jsonify({"error": "User not found"}), 404
#     db.session.delete(user)
#     db.session.commit()
#     return jsonify(user.serialize()), 200

# @app.route('/api/rank_by_distance', methods=['GET'])
# def rank_by_distance(): #✅
#     """
#     Rank dining halls by distance from user
#     """
#     user_latitude = request.args.get('latitude', type=float)
#     user_longitude = request.args.get('longitude', type=float)
#     all_dining_halls = DiningHall.query.all()
#     dining_and_distance = []
#     for hall in all_dining_halls:
#         dining_and_distance.append({
#             "dining_hall": hall.serialize(user_latitude, user_longitude),
#             "distance": hall.calculate_distance(user_latitude, user_longitude)
#         })
#     return jsonify(dining_and_distance), 200

@app.route('/api/swipe', methods=['POST'])
def swipe():
    """
    Swipe on a menu item
    """
    data = request.get_json()
    user_id = data.get('userId')
    menu_item_id = data.get('menuItemId')
    swipe_boolean = data.get('swipeBoolean')

    if None in [user_id, menu_item_id, swipe_boolean]:
        return jsonify({"error": "Missing required fields"}), 400

    user = User.query.get(user_id)
    menu_item = MenuItem.query.get(menu_item_id)

    if not user or not menu_item:
        return jsonify({"error": "Invalid user or menu item"}), 404
    swipe = Swipe(
        userId=user_id,
        menu_item_id=menu_item_id,
        swipeBoolean=swipe_boolean
    )
    db.session.add(swipe)

    if swipe_boolean:
        for dininghall in menu_item.dininghalls:
            dininghall.swipeCount +=1

    db.session.commit()
    return jsonify(swipe.serialize()), 201

@app.route('/api/userSwipe/<int:user_id>', methods=['GET'])
def get_user_swipe(user_id):
    """
    Get the swipe for a user
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    swipes = Swipe.query.filter_by(userId=user_id).all()
    
    return jsonify([swipe.serialize() for swipe in swipes]), 200


@app.route('/api/dining/menu/<string:name>', methods = ['GET'])
def get_dining_hall_menu(name): 
    """
    Get the menu for a dining hall
    """
    dining_hall= DiningHall.query.filter_by(name=name).first()
    if dining_hall is None:
        return jsonify({"error":"Dining hall was not found"}), 404
    menu_items = [item.name for item in dining_hall.menu_items]
    return jsonify({
        "dining_hall": name,
        "menu_items": menu_items
    }), 200


@app.route('/api/item/<string:name>', methods = ['GET'])
def get_item_dining_halls(name):
    """
    Get the dining halls an item is in
    """
    item = MenuItem.query.filter_by(name=name).first()
    if item is None:
        return jsonify({"error":"Item was not found"}), 404
    
    dining_halls = [hall.name for hall in item.dining_halls]

    return jsonify({
        "item": name,
        "menu_items": dining_halls
    }), 200

@app.route('/api/dininghalls', methods=['DELETE'])
def delete_dining_hall_swipes(): 
    """
    Delete all swipes for all dining hall
    """
    dining_halls = DiningHall.query.all()
    for dining_hall in dining_halls:
        dining_hall.swipeCount = 0
    db.session.commit()
    return jsonify({"message": "All swipes deleted"}), 200


@app.route('/api/menu', methods=['POST'])
def add_menu():
    """
    Add a menu to the database
    """
    data = request.get_json()
    name = data.get('name')
    dining_hall_id = data.get('diningHallId')

    if not all([name, dining_hall_id]):
        return jsonify({"error": "Missing required fields"}), 400

    dining_hall = DiningHall.query.get(dining_hall_id)
    if not dining_hall:
        return jsonify({"error": "Dining hall not found"}), 404

    menu = Menu(name=name, dining_hall=dining_hall)

    db.session.add(menu)
    db.session.commit()
    return jsonify(menu.serialize()), 201


@app.route('/api/menuitems', methods=['POST'])
def add_menu_items(): #works
    """
    Add menu items to the database
    """
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    photo = data.get('photo')
    menu_ids = data.get('menuIds')  # list of menu IDs

    if not all([name, description, photo]) or not isinstance(menu_ids, list) or not menu_ids:
        return jsonify({"error": "Missing or invalid required fields"}), 400

    menu_item = MenuItem(name=name, description=description, photo=photo)

    for menu_id in menu_ids:
        menu = Menu.query.get(menu_id)
        if not menu:
            return jsonify({"error": f"Menu with ID {menu_id} not found"}), 404
        menu_item.menus.append(menu)

    db.session.add(menu_item)
    db.session.commit()
    return jsonify(menu_item.serialize()), 201

@app.route('/api/menuitems', methods=['GET'])
def get_menu_items(): #works obviously
    '''
    Get all menu items in database
    '''
    menu_items = MenuItem.query.all()
    return jsonify([item.serialize() for item in menu_items]), 200

@app.route('/api/menuitems/<int:item_id>', methods=['GET'])
def get_specific_menu_item(item_id): #works
    '''
    Get specific menu item by item id
    '''
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404
    return jsonify(item.serialize()), 200


# @app.route('/api/match/<int:user_id>', methods=['GET'])
# def match_dining_hall(user_id):
#     """
#     Get the dining hall that matches the user's swipes
#     """
#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({"error": "User not found"}), 404
    
#     dining_halls = DiningHall.query.all()
#     if not dining_halls:
#         return jsonify({"error": "No dining halls found"}), 404

#     max_swipe = max(hall.swipeCount for hall in dining_halls)
#     matched_halls = [hall.serialize() for hall in dining_halls if hall.swipeCount == max_swipe]

#     return jsonify({"dining_hall": matched_halls}), 200



@app.route('/api/dininghalls', methods=['POST'])
def create_dining_hall(): #works
    """
    Create a dining hall
    """
    data = request.get_json()
    name = data.get('name')

    if name is None:
        return jsonify({"error": "Missing required fields"}), 400

    hall = DiningHall(name=name)
    db.session.add(hall)
    db.session.commit()
    return jsonify(hall.serialize()), 201


#TRYING TO IMPLEMENT USING THE TABLE
@app.route('/api/match2/<int:user_id>', methods=['GET'])
def match_dining_hall(user_id):
    """
    Get the dining hall that matches the user's swipes
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    swipes = user.user_swipe_table_entries
    if not swipes:
        return jsonify({"error": "No swipes found for this user"}), 404
    
    dininghall_counts = defaultdict(int)

    for swipe in swipes:
        if swipe.swipeBoolean:
            menu_item = swipe.menu_item
            for dining_hall in menu_item.dining_halls:
                # dining_hall.swipeCount += 1    
                dininghall_counts[dining_hall.id] += 1
    max_count = max(dininghall_counts.values())
    matched_hall_id = max(dininghall_counts, key=lambda k: (dininghall_counts[k], -k)) # For now, this just takes the lowest id if multiple have same swipe count
    matched_hall = DiningHall.query.get(matched_hall_id)
    return jsonify({"dining_hall": matched_hall}), 200



# @app.route('/api/upload', methods=['POST'])
# def upload_photos():
#     picture = request.files.get['picture']
#     menu_item_id = request.form.get('menuItemId')
#     dining_hall_id = request.form.get('diningHallId')

#     if picture is None:
#         return jsonify({"error": "No picture"}),404
    
#     filename = secure_filename(picture.filename)
#     filepath = os.path.join("static/uploads", picture.filename)
#     picture.save(filepath)

#     plate = PlatePhotos(
#         menuItemId=menu_item_id,
#         diningHallId= dining_hall_id,
#         photo=picture
#     )

#     db.session.add(plate)
#     db.session.commit()
#     return jsonify(plate.serialize()),201


# @app.route('/api/clear_database', methods=['POST'])
# def clear_database():
#     try:
#         # Delete in reverse order of dependencies
#         Swipe.query.delete()
#         MenuItem.query.delete()
#         DiningHall.query.delete()
#         User.query.delete()
        
#         db.session.commit()
#         return jsonify({'message': 'All data deleted'}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

