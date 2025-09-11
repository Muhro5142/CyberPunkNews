from flask import Flask, render_template, request, redirect, url_for, make_response, session
import time
from managerdb import ManagerDB
import subart2

server = Flask(__name__)
server.secret_key = 'your_secret_key_here'  # Add a secret key for session

# server routes!
authusers = []

@server.route('/')
def index():
    test = request.cookies.get("index")
    page = "/"
    db = ManagerDB("db.db")
    newslist = db.fetchnews()
    news = []
    strs_en = []
    strs_ru = []
    
    # Get language preference from session or set default to Russian
    lang_pref = session.get('websiteLang', 1)  # Default to Russian (1)
    
    for new in newslist:
        str_en = new[3]
        str_ru = new[2]
        strs_en.append(str_en.split("\n"))
        strs_ru.append(str_ru.split("\n"))
    
    # Pull and clear submission status
    submit_status = session.pop('submit_status', None)

    if lang_pref == 1:  # Russian
        for str_ru in strs_ru:
            location, title, summary, time = "", "", "", ""
            for line in str_ru:
                if "Локация" in line:
                    location = line[9:]
                if "Время" in line:
                    time = line[6:]
                if "Заголовок" in line:
                    title = line[10:]
                if "Сводка" in line:
                    summary = line[8:]
            news.append({"title": title, "summary": summary, "time": time, "location": location})

        return render_template('index.html', page=page, test=test, news=news, submit_status=submit_status)
    else:  # English
        for str_en in strs_en:
            location, title, summary, time = "", "", "", ""
            for line in str_en:
                if "Location" in line:
                    location = line[9:]
                if "Time" in line:
                    time = line[5:]
                if "Headline" in line:
                    title = line[9:]
                if "Summary" in line:
                    summary = line[8:]
            news.append({"title": title, "summary": summary, "time": time, "location": location})
        return render_template('indexeng.html', page=page, test=test, news=news, submit_status=submit_status)

@server.route('/reg', methods=['POST', 'GET'])
def reg():
    db = ManagerDB("db.db")
    page = "/reg"
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        print(name, email, password)

        try:
            db.insertuser(name, email, password)
        except:
            return render_template("reg.html", page=page, error="User already exists")

        user = db.usersearch(email)
        authusers.append(user[0][0])
        resp = make_response(redirect('/'))
        resp.set_cookie("index", str(user[0][0]))
        print(authusers)

        return resp
    return render_template('reg.html', page=page)

@server.route('/log', methods=['POST', 'GET'])
def log():
    db = ManagerDB("db.db")
    page = "/log"
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.usersearch(email)
        print(user)

        if not user:
            return render_template("log.html", page=page, error="User not found")

        print(user[0][3], password)
        print([password])

        if user[0][3] != password:
            return render_template("log.html", page=page, error="Wrong password")

        resp = make_response(redirect('/'))
        authusers.append(user[0][0])
        resp.set_cookie("index", str(user[0][0]))
        print(authusers)

        return resp
    return render_template('log.html', page=page)

@server.route('/submitart', methods=['POST', 'GET'])
def submitart():
    db = ManagerDB("db.db")
    page = "/submitart"
    user_id = request.cookies.get("index")

    if user_id is None:
        return redirect('/log')
    
    # Check if user exists in database instead of authusers list
    user = db.fetchuserbyid(user_id)
    if not user:
        return redirect('/log')

    error = None
    success = None
    
    if request.method == 'POST':
        # Basic anti-spam: per-user cooldown and window cap
        now = time.time()
        cooldown_seconds = 5
        window_seconds = 60
        window_max = 5

        last_time = session.get('last_submit_time')
        window_start = session.get('submit_window_start')
        window_count = session.get('submit_window_count', 0)

        # Initialize window if missing or expired
        if not window_start or now - window_start > window_seconds:
            window_start = now
            window_count = 0

        # Enforce cooldown
        if last_time and (now - last_time) < cooldown_seconds:
            print("Submit blocked by cooldown")
            return redirect('/')

        # Enforce window maximum
        if window_count >= window_max:
            print("Submit blocked by rate limit window")
            return redirect('/')

        prompt = request.form['submitartinput']
        print(f"Processing prompt: {prompt}")

        # Update rate limit counters before calling LLM to guard against concurrent posts
        session['last_submit_time'] = now
        session['submit_window_start'] = window_start
        session['submit_window_count'] = window_count + 1

        # Use the modified query_model function that returns validation status
        output, is_valid = subart2.query_model(prompt)
        
        if is_valid:
            english, sep, russian = output.partition('---')
            db.insertnews(user_id, russian, english)
            print(f"Inserted news for user {user_id}: {russian}, {english}")
            session['submit_status'] = 'success'
        else:
            print("Submission failed validation; nothing inserted.")
            session['submit_status'] = 'error'

        # Always redirect to main page after POST
        return redirect('/')

    return render_template('submitart.html', page=page, error=error, success=success)

@server.route('/lang', methods=['POST'])
def lang():
    if request.method == 'POST':
        page = request.form['page']
        
        # Toggle language in session
        current_lang = session.get('websiteLang', 1)
        session['websiteLang'] = 2 if current_lang == 1 else 1
        
        # Create a response that redirects and ensures the cookie is set
        response = make_response(redirect(page))
        return response

if __name__ == '__main__':
    server.run(debug=True)
