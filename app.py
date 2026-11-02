
from flask import Flask, request, session, redirect, url_for, render_template_string, send_from_directory, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, subprocess, json, time

APP_DIR=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(APP_DIR,"nvm.db")
UPLOAD=os.path.join(APP_DIR,"uploads")
os.makedirs(UPLOAD, exist_ok=True)
app=Flask(__name__)
app.secret_key="change-this-secret-key"
app.config["MAX_CONTENT_LENGTH"]=32*1024*1024

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username UNIQUE, password, role TEXT DEFAULT 'user', created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS nodes(id INTEGER PRIMARY KEY, name, host, type TEXT DEFAULT 'local', status TEXT DEFAULT 'online', created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS servers(id INTEGER PRIMARY KEY, name, node_id INTEGER, owner_id INTEGER, type TEXT, status TEXT DEFAULT 'stopped', cpu INTEGER DEFAULT 1, ram INTEGER DEFAULT 512, disk INTEGER DEFAULT 10, ip TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS subusers(id INTEGER PRIMARY KEY, server_id INTEGER, username, password, permissions TEXT DEFAULT 'console,filemanager,ports', created TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    if not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",("admin",generate_password_hash("admin123"),"admin"))
    if not c.execute("SELECT 1 FROM nodes").fetchone():
        c.execute("INSERT INTO nodes(name,host,type,status) VALUES(?,?,?,?)",("Local Node","127.0.0.1","local","online"))
    c.commit(); c.close()
init()

def current_user():
    if "uid" not in session: return None
    c=db(); u=c.execute("SELECT * FROM users WHERE id=?",(session["uid"],)).fetchone(); c.close(); return u

def login_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a,**k):
        u=current_user()
        if not u: return redirect(url_for("login"))
        return f(u,*a,**k)
    return w

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a,**k):
        u=current_user()
        if not u: return redirect(url_for("login"))
        if u["role"]!="admin": abort(403)
        return f(u,*a,**k)
    return w

def setting(key,default=""):
    c=db(); r=c.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone(); c.close()
    return r["value"] if r else default

BASE=r"""
<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>NVM Panel</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#0b1020;color:#e7ecf5;display:flex;min-height:100vh}
.sidebar{width:250px;background:#0f172b;border-right:1px solid #1e2a44;padding:18px;flex-shrink:0}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px;margin-bottom:22px}
.brand img{width:34px;height:34px;border-radius:8px;object-fit:cover}
.nav a{display:block;padding:11px 13px;border-radius:10px;color:#c8d3e8;text-decoration:none;margin-bottom:6px}
.nav a:hover,.nav a.active{background:#1b2a4a;color:#fff}
.main{flex:1;padding:26px;overflow:auto}
.card{background:#111a30;border:1px solid #1e2a44;border-radius:14px;padding:18px;margin-bottom:16px}
h1,h2{margin:0 0 14px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #1e2a44}
input,select,textarea{width:100%;padding:10px;border-radius:9px;border:1px solid #26365a;background:#0b1224;color:#fff;margin:5px 0 12px}
button,.btn{background:#3b82f6;color:#fff;border:0;padding:10px 15px;border-radius:9px;cursor:pointer;text-decoration:none;display:inline-block}
.btn.red{background:#ef4444}.btn.green{background:#22c55e}.btn.gray{background:#475569}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.badge{padding:3px 9px;border-radius:999px;font-size:12px;background:#1e293b}
.flash{background:#14532d;border:1px solid #22c55e;padding:10px;border-radius:9px;margin-bottom:12px}
</style></head><body>
<div class=sidebar>
 <div class=brand>{% if logo %}<img src="/uploads/{{logo}}">{% endif %} {{panel_name}}</div>
 <div class=nav>
  <a href="/">Account Info</a>
  {% if u.role=='admin' %}
   <a href="/admin">Admin Panel</a>
   <a href="/admin/nodes">Machines</a>
   <a href="/admin/servers">Servers</a>
   <a href="/admin/users">Users</a>
   <a href="/admin/branding">Branding</a>
  {% endif %}
  <a href="/servers">My Servers</a>
 </div>
</div>
<div class=main>{% if msg %}<div class=flash>{{msg}}</div>{% endif %}{{body|safe}}</div>
</body></html>
"""

def page(title,body,u,msg=None):
    return render_template_string(BASE,title=title,body=body,u=u,msg=msg,panel_name=setting("panel_name","NVM Panel"),logo=setting("logo"))

@app.route("/uploads/<path:f>")
def uploads(f): return send_from_directory(UPLOAD,f)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM users WHERE username=?",(request.form["username"],)).fetchone(); c.close()
        if u and check_password_hash(u["password"],request.form["password"]):
            session["uid"]=u["id"]; return redirect("/")
        return render_template_string(BASE,title="Login",body="<h1>Login</h1><form method=post>Username<input name=username><br>Password<input name=password type=password><br><button>Login</button></form>",u=None,panel_name=setting("panel_name","NVM Panel"),logo=setting("logo"),msg="Invalid login")
    return render_template_string(BASE,title="Login",body="<h1>Login to NVM Panel</h1><form method=post>Username<input name=username><br>Password<input name=password type=password><br><button>Login</button></form>",u=None,panel_name=setting("panel_name","NVM Panel"),logo=setting("logo"))

@app.route("/logout")
def logout(): session.clear(); return redirect("/login")

@app.route("/")
@login_required
def home(u):
    body=f"<h1>Account Info</h1><div class=card><b>Username:</b> {u['username']}<br><b>Role:</b> {u['role']}<br><b>Created:</b> {u['created']}</div>"
    return page("Account",body,u)

@app.route("/servers")
@login_required
def my_servers(u):
    c=db()
    rows=c.execute("SELECT s.*,n.name node FROM servers s JOIN nodes n ON n.id=s.node_id WHERE s.owner_id=?",(u["id"],)).fetchall()
    cards="".join(f"<div class=card><b>{r['name']}</b><br>{r['type'].upper()} | {r['status']}<br>Node: {r['node']}<br><a class=btn href='/server/{r['id']}'>Open</a></div>" for r in rows)
    return page("My Servers",f"<h1>My Servers</h1><div class=grid>{cards or '<p>No servers yet.</p>'}</div>",u)

@app.route("/server/<int:sid>")
@login_required
def server_view(u,sid):
    c=db(); s=c.execute("SELECT * FROM servers WHERE id=? AND owner_id=?",(sid,u["id"])).fetchone(); c.close()
    if not s: abort(404)
    body=f"""<h1>{s['name']} <span class=badge>{s['type'].upper()} / {s['status']}</span></h1>
    <div style=display:flex;gap:20px><div class=sidebar style=width:220px>
    <a class=btn style=width:100% href='/server/{sid}/console'>Console</a><br><br>
    <a class=btn style=width:100% href='/server/{sid}/files'>File Manager</a><br><br>
    <a class=btn style=width:100% href='/server/{sid}/ports'>Forward Port</a><br><br>
    <a class=btn style=width:100% href='/server/{sid}/subusers'>Subusers</a></div>
    <div class=card style=flex:1><h2>Resources</h2>CPU: {s['cpu']} vCore<br>RAM: {s['ram']} MB<br>Disk: {s['disk']} GB<br>IP: {s['ip'] or 'auto'}</div></div>"""
    return page("Server",body,u)

@app.route("/server/<int:sid>/console",methods=["GET","POST"])
@login_required
def console(u,sid):
    c=db(); s=c.execute("SELECT * FROM servers WHERE id=? AND owner_id=?",(sid,u["id"])).fetchone(); c.close()
    if not s: abort(404)
    out=""
    if request.method=="POST":
        a=request.form["action"]
        if s["type"]=="lxc":
            cmd={"start":["lxc-start","-n",s["name"],"-d"],"stop":["lxc-stop","-n",s["name"]],"restart":["lxc-stop","-n",s["name"]],"reboot":["lxc-stop","-n",s["name"]]}.get(a)
        else:
            cmd={"start":["virsh","start",s["name"]],"stop":["virsh","shutdown",s["name"]],"restart":["virsh","reboot",s["name"]],"reboot":["virsh","reboot",s["name"]]}.get(a)
        if cmd:
            try: out=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            except Exception as e: out=str(e)
    buttons="".join(f"<form method=post style=display:inline><input type=hidden name=action value={a}><button class='btn {cls}'>{a.title()}</button></form> " for a,cls in [("start","green"),("stop","red"),("restart","gray")])
    if s["type"]=="kvm": buttons+=f"<form method=post style=display:inline><input type=hidden name=action value=reboot><button class='btn red'>Reboot</button></form>"
    body=f"<h1>Console</h1><div class=card>{buttons}<pre>{out}</pre></div><a href='/server/{sid}'>Back</a>"
    return page("Console",body,u)

@app.route("/server/<int:sid>/files")
@login_required
def files(u,sid):
    c=db(); s=c.execute("SELECT * FROM servers WHERE id=? AND owner_id=?",(sid,u["id"])).fetchone(); c.close()
    if not s: abort(404)
    path=request.args.get("path","/")
    if not os.path.isdir(path): path="/"
    try: entries=sorted(os.listdir(path))
    except Exception as e: entries=[]; path=f"/ ({e})"
    rows="".join(f"<tr><td>{e}</td><td><a class=btn href='/server/{sid}/files?path={path.rstrip('/')}/{e}'>Open</a></td></tr>" for e in entries)
    body=f"<h1>File Manager</h1><div class=card><b>Path:</b> {path}<br><a class=btn href='/server/{sid}/files?path=/'>Go to main root (/)</a><table><tr><th>Name</th><th></th></tr>{rows}</table></div><a href='/server/{sid}'>Back</a>"
    return page("Files",body,u)

@app.route("/server/<int:sid>/ports",methods=["GET","POST"])
@login_required
def ports(u,sid):
    c=db(); s=c.execute("SELECT * FROM servers WHERE id=? AND owner_id=?",(sid,u["id"])).fetchone(); c.close()
    if not s: abort(404)
    out=""
    if request.method=="POST":
        p=request.form.get("port","")
        if p.isdigit():
            try:
                r=subprocess.Popen(["ssh","-o","StrictHostKeyChecking=no","-p","443",f"-R0:localhost:{p}","a.pinggy.io"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                time.sleep(3); out="Tunnel process started. Check pinggy output in server logs."
            except Exception as e: out=str(e)
    body=f"<h1>Forward Port</h1><div class=card><p>Creates a public HTTPS/TCP tunnel using <b>pinggy.io</b>.</p><form method=post>Local port<input name=port placeholder='e.g. 8080'><button>Create Tunnel</button></form><pre>{out}</pre></div><a href='/server/{sid}'>Back</a>"
    return page("Ports",body,u)

@app.route("/server/<int:sid>/subusers",methods=["GET","POST"])
@login_required
def subusers(u,sid):
    c=db(); s=c.execute("SELECT * FROM servers WHERE id=? AND owner_id=?",(sid,u["id"])).fetchone()
    if not s: abort(404)
    if request.method=="POST":
        c.execute("INSERT INTO subusers(server_id,username,password,permissions) VALUES(?,?,?,?)",(sid,request.form["username"],generate_password_hash(request.form["password"]),request.form.get("permissions","console,filemanager,ports")))
        c.commit()
    subs=c.execute("SELECT * FROM subusers WHERE server_id=?",(sid,)).fetchall()
    rows="".join(f"<tr><td>{x['username']}</td><td>{x['permissions']}</td></tr>" for x in subs)
    body=f"<h1>Subusers</h1><div class=card><form method=post>Username<input name=username><br>Password<input name=password type=password><br>Permissions<input name=permissions value='console,filemanager,ports'><button>Add Subuser</button></form><table><tr><th>User</th><th>Permissions</th></tr>{rows}</table></div><a href='/server/{sid}'>Back</a>"
    return page("Subusers",body,u)

@app.route("/admin")
@admin_required
def admin(u):
    c=db()
    stats=[("Users",c.execute("SELECT COUNT(*) FROM users").fetchone()[0]),("Nodes",c.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]),("Servers",c.execute("SELECT COUNT(*) FROM servers").fetchone()[0])]
    body="<h1>Admin Panel</h1><div class=grid>"+"".join(f"<div class=card><h2>{n}</h2>{v}</div>" for n,v in stats)+"</div>"
    return page("Admin",body,u)

@app.route("/admin/nodes",methods=["GET","POST"])
@admin_required
def nodes(u):
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO nodes(name,host,type,status) VALUES(?,?,?,?)",(request.form["name"],request.form["host"],request.form["type"],"online")); c.commit()
    rows=c.execute("SELECT * FROM nodes").fetchall()
    tr="".join(f"<tr><td>{r['name']}</td><td>{r['host']}</td><td>{r['type']}</td><td>{r['status']}</td></tr>" for r in rows)
    body=f"<h1>Machines / Nodes</h1><div class=card><form method=post>Name<input name=name><br>Host / IP<input name=host><br>Type<select name=type><option>remote</option><option>local</option></select><button>Add Node</button></form></div><div class=card><table><tr><th>Name</th><th>Host</th><th>Type</th><th>Status</th></tr>{tr}</table></div>"
    return page("Nodes",body,u)

@app.route("/admin/servers",methods=["GET","POST"])
@admin_required
def admin_servers(u):
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO servers(name,node_id,owner_id,type,cpu,ram,disk,ip) VALUES(?,?,?,?,?,?,?,?)",(request.form["name"],request.form["node_id"],request.form["owner_id"],request.form["type"],request.form["cpu"],request.form["ram"],request.form["disk"],request.form["ip"])); c.commit()
    rows=c.execute("SELECT s.*,n.name node,us.username owner FROM servers s JOIN nodes n ON n.id=s.node_id JOIN users us ON us.id=s.owner_id").fetchall()
    tr="".join(f"<tr><td>{r['name']}</td><td>{r['type']}</td><td>{r['node']}</td><td>{r['owner']}</td><td>{r['status']}</td><td><a class=btn href='/server/{r['id']}'>Open</a></td></tr>" for r in rows)
    users=c.execute("SELECT id,username FROM users").fetchall(); nodes=c.execute("SELECT id,name FROM nodes").fetchall()
    opts_u="".join(f"<option value={x['id']}>{x['username']}</option>" for x in users)
    opts_n="".join(f"<option value={x['id']}>{x['name']}</option>" for x in nodes)
    body=f"<h1>Servers</h1><div class=card><form method=post>Name<input name=name><br>Node<select name=node_id>{opts_n}</select><br>Owner<select name=owner_id>{opts_u}</select><br>Type<select name=type><option>lxc</option><option>kvm</option></select><br>CPU<input name=cpu value=1><br>RAM MB<input name=ram value=512><br>Disk GB<input name=disk value=10><br>IP<input name=ip placeholder=optional><button>Create Server</button></form></div><div class=card><table><tr><th>Name</th><th>Type</th><th>Node</th><th>Owner</th><th>Status</th><th></th></tr>{tr}</table></div>"
    return page("Servers",body,u)

@app.route("/admin/users",methods=["GET","POST"])
@admin_required
def admin_users(u):
    c=db()
    if request.method=="POST":
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",(request.form["username"],generate_password_hash(request.form["password"]),request.form["role"])); c.commit()
    rows=c.execute("SELECT * FROM users").fetchall()
    tr="".join(f"<tr><td>{r['username']}</td><td>{r['role']}</td><td>{r['created']}</td></tr>" for r in rows)
    body=f"<h1>Users</h1><div class=card><form method=post>Username<input name=username><br>Password<input name=password type=password><br>Role<select name=role><option>user</option><option>admin</option></select><button>Create User</button></form></div><div class=card><table><tr><th>Username</th><th>Role</th><th>Created</th></tr>{tr}</table></div>"
    return page("Users",body,u)

@app.route("/admin/branding",methods=["GET","POST"])
@admin_required
def branding(u):
    c=db()
    if request.method=="POST":
        if request.form.get("panel_name"): c.execute("INSERT OR REPLACE INTO settings VALUES('panel_name',?)",(request.form["panel_name"],))
        for k in ["logo","background"]:
            f=request.files.get(k)
            if f and f.filename:
                fn=secure_filename(f.filename); f.save(os.path.join(UPLOAD,fn)); c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(k,fn))
        c.commit()
    body=f"""<h1>Branding</h1><div class=card><form method=post enctype=multipart/form-data>
    Panel name<input name=panel_name value='{setting("panel_name","NVM Panel")}'><br>
    Logo<input type=file name=logo><br>Background<input type=file name=background><br>
    <button>Save</button></form></div>
    <div class=card>Current logo: {setting('logo','none')}<br>Current background: {setting('background','none')}</div>"""
    return page("Branding",body,u)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=6767,debug=False)
