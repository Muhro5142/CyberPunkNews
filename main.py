
from flask import Flask, render_template, request,redirect, url_for,make_response
from managerdb import ManagerDB
import subart2

server = Flask(__name__)
websiteLang = 1
#server routes!
authusers = []
@server.route('/') 
def index():
    test = request.cookies.get("index")
    print(test,len(authusers)-1)
    page = "/"
    if websiteLang == 1:
        return render_template('index.html',page = page,test = test)
    else:
        return render_template('indexeng.html', page = page,test = test)
    

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
            return render_template("reg.html", page = page, error = "User already exists")

        
        user = db.usersearch(email)
        authusers.append(user[0][0])
        resp = make_response(redirect('/'))
        resp.set_cookie("index", str(user[0][0]))
        print(authusers)
        
        return resp
    return render_template('reg.html', page = page)


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
            return render_template("log.html", page = page, error = "User not found")
        
        print(user[0][3],password)
        print([password])

        if user[0][3] != password:
            return render_template("log.html", page = page, error = "Wrong password")
        
        resp = make_response(redirect('/'))
        authusers.append(user[0][0])
        resp.set_cookie("index", str(user[0][0]))
        print(authusers)
        

        return resp
    return render_template('log.html', page = page)
    

@server.route('/submitart', methods=['POST', 'GET'])
def submitart():
    db = ManagerDB("db.db")
    page = "/submitart"
    if request.method == 'POST':
        prompt = request.form['submitartinput']
        print(prompt)
        output = subart2.query_model(prompt)
        english, sep, russian = output.partition('---')
        print(english, sep,russian)
        db.insertnews(request.cookies.get("index"), russian, english)
        
        
        
    return render_template('submitart.html', page = page)
    


@server.route('/lang', methods=['POST'])
def lang():

    if request.method == 'POST':
        global websiteLang
        page = request.form['page']

        if websiteLang == 1:
            websiteLang = 2
        else:
            websiteLang = 1
        
        return redirect(page)


if __name__ == '__main__':
    server.run(debug=True)