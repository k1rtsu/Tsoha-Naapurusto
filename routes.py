from app import app
import secrets
from flask import render_template, request, redirect, session, abort, flash
import users
from regions import get_regions, regions_posts_count, regions_topics_count, get_region, search_regions, create_region, delite_region
from topics import get_topics, topic_posts_count, get_topic, create_topic, delete_topic, get_author, search_topics
from posts import get_posts, create_post, get_user_posts, delite_post, search_posts, get_post
from comments import create_comment, get_comments_for_post, delete_comment, get_comment


#MAIN_PAGE
@app.route("/")
def index():
    username = session.get('username')
    regions = get_regions()
    
    post_count = regions_posts_count()
    topic_count = regions_topics_count()
    user_posts = get_user_posts()

    return render_template("index.html", username=username, regions=regions, 
                           regions_topic_count=topic_count, regions_post_count=post_count,
                           user_posts=user_posts)


#CREATE_REGION(ADMIN)
@app.route("/create_region", methods=["GET", "POST"])
def create_new_region():
    if session.get("role") != "admin":
        return redirect("/")
    if request.method == "GET":
        return render_template("create_region.html")
    
    if request.method == "POST":
        if session.get("csrf_token") != request.form["csrf_token"]:
            abort(403)
        name = request.form.get("name")
        description = request.form.get("description")
        if not name or not description:
            return render_template("create_region.html", error="Name and description are required.")
        
        create_region(name, description)
        return redirect("/")
    
#DELETE_REGION(ADMIN)
@app.route("/delete_region/<int:region_id>", methods=["POST"])
def delete_region(region_id):
    if session.get("role") != "admin":
        return redirect("/")
    delite_region(region_id)
    flash("Region poistettu onnistuneesti.")
    return redirect("/")


#CREATE_ACCOUNT
@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'GET':
        session['csrf_token'] = secrets.token_hex(16)
        return render_template("create_account.html", csrf_token=session['csrf_token'])
    
    if request.method == 'POST':
        if session.get('csrf_token') != request.form.get('csrf_token'):
            abort(403)  
        
        username = request.form['username']
        password = request.form['password']


        if len(username) < 3 or len(username) > 50:
            return render_template("create_account.html", error="Username must be 3-50 characters long.", csrf_token=session['csrf_token'])
        if len(password) < 8:
            return render_template("create_account.html", error="Password must be at least 8 characters long.", csrf_token=session['csrf_token'])

        if users.create_account(username, password):
            return redirect('/')
        
        return render_template("create_account.html", error="Username already taken or registration failed.", csrf_token=session['csrf_token'])


#LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        session['csrf_token'] = secrets.token_hex(16)
        return render_template("login.html", csrf_token=session['csrf_token'])
    
    if request.method == 'POST':
        if session['csrf_token'] != request.form['csrf_token']:
            abort(403)
        username = request.form['username']
        password = request.form['password']
        if users.login(username, password):
            return redirect('/')
        return render_template("login.html", error="Wrong username or password", csrf_token=session['csrf_token'])

#LOGOUT
@app.route('/logout')
def logout():
    users.logout()
    return redirect('/')

#REGION
@app.route("/region/<int:region_id>")
def region(region_id):
    region = get_region(region_id)
    topics = get_topics(region_id)
    topics_with_post_counts = [
        {
            "id": topic[0],
            "title": topic[2],
            "description": topic[3],
            "post_count": topic_posts_count(topic[0]),
        }
        for topic in topics
    ]
    return render_template("region.html", region=region, topics=topics_with_post_counts)


#TOPIC
@app.route("/topic/<int:topic_id>", methods=["GET", "POST"])
def topic(topic_id):
    user_id = session.get("user_id")
    
    topic = get_topic(topic_id)
    posts = get_posts(topic_id)
    author = session.get("username")
    author_id = get_author(topic_id)
    role = session.get("role")
    
    post_comments = {}
    for post in posts:
        post_comments[post.id] = get_comments_for_post(post.id)
    
    if request.method == "POST":
        if session.get("csrf_token") != request.form["csrf_token"]:
            abort(403)
        if author_id == user_id or role == "admin":
            delete_topic(topic_id)
            flash("Topic poistettu onnistuneesti.")
            return redirect("/")
        else:
            flash("Sinulla ei ole oikeuksia poistaa tätä topicia.")
            return redirect(f"/topic/{topic_id}")
    
    return render_template("topic.html", topic=topic, posts=posts, author=author, author_id=author_id, role=role, post_comments=post_comments)


#NEW_TOPIC
@app.route("/region/<int:region_id>/new_topic", methods=["GET", "POST"])
def new_topic(region_id):
    if request.method == "GET":
        region = get_region(region_id)
        if not region:
            abort(404)  
        return render_template("new_topic.html", region=region)
    
    if request.method == "POST":
        if session.get("csrf_token") != request.form.get("csrf_token"):
            abort(403)

        title = request.form["title"]
        description = request.form["description"]
        user_id = session.get("user_id")
        
        if not user_id:
            return redirect("/login")
        
        if len(title) < 5 or len(title) > 200:
            return render_template("new_topic.html", region=get_region(region_id), error="Title must be 5-200 characters long.")
        
        if create_topic(region_id, title, description, user_id):
            return redirect(f"/region/{region_id}")
        else:
            return render_template("new_topic.html", region=get_region(region_id), error="Failed to create topic.")


#NEW_POST
@app.route("/topic/<int:topic_id>/new_post", methods=["GET", "POST"])
def new_post(topic_id):
    if request.method == "GET":
        return render_template("new_post.html", topic={"id": topic_id})

    if request.method == "POST":
        if session.get("csrf_token") != request.form["csrf_token"]:
            abort(403)
        content = request.form.get("content")
        if not content:
            return "Content is required", 400

        if create_post(topic_id, content):
            return redirect(f"/topic/{topic_id}")
        return "Error creating post", 500


#DELETE_POST
@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Et ole kirjautunut sisään.")
        return redirect("/login")
 
    delite_post(post_id)
    flash("Postau poistettu onnistuneesti.")
    return redirect("/")

#REGION_SEARCH
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").strip()
    if not query:
        flash("Anna hakusana.")
        return redirect("/")
    
    results = search_regions(query)
    
    return render_template("search_results_regions.html", query=query, results=results)

#TOPICT_SEARCH
@app.route("/region/<int:region_id>/topic_search", methods=["GET"])
def topic_search(region_id):
    query = request.args.get("query", "").strip()
    
    if not query:
        flash("Anna hakusana.")
        return redirect(f"/region/{region_id}")
    
    results = search_topics(query, region_id)
    
    return render_template("search_results_topics.html", query=query, results=results, region_id=region_id)


#POST_SEARCH
@app.route("/post_search", methods=["GET"])
def post_search():
    query = request.args.get("query", "").strip()
    topic_id = request.args.get("topic_id")
    
    if not query:
        flash("Anna hakusana.")
        return redirect(f"/topic/{topic_id}")
    
    results = search_posts(query, topic_id)
    
    return render_template("search_results_posts.html", query=query, results=results, topic_id=topic_id)

#CREATE_COMMENT
@app.route("/post/<int:post_id>/add_comment", methods=["POST"])
def add_comment(post_id):
    if session.get("csrf_token") != request.form["csrf_token"]:
        abort(403)
    content = request.form.get("content", "").strip()
    if not content:
        flash("Kommentti ei voi olla tyhjä.")
        return redirect(f"/post/{post_id}")

    if create_comment(post_id, content):
        flash("Kommentti lisätty!")
    else:
        flash("Virhe lisättäessä kommenttia.")
    return redirect(f"/topic/{get_post(post_id).topic_id}")


#DELETE_COMMENT
@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment_route(comment_id):
    if session.get("csrf_token") != request.form["csrf_token"]:
        abort(403)
    post_id = get_comment(comment_id).post_id
    topic_id = get_post(post_id).topic_id

    if delete_comment(comment_id):
        flash("Kommentti poistettu onnistuneesti.")
    else:
        flash("Kommentin poistaminen epäonnistui.")

    return redirect(f"/topic/{topic_id}")
