import hashlib, json, os, re, secrets, sqlite3, urllib.parse, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Ho_Chi_Minh')
from pathlib import Path
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('THIENHA_DATA_DIR', str(ROOT/'data')))
FILES=DATA/'files'; DB=DATA/'users.db'
ADMIN=os.environ.get('THIENHA_ADMIN_EMAIL', 'eric.scorp93@gmail.com').lower(); ALLOWED={'.bin','.hex','.uf2','.zip','.tar','.gz','.md','.pdf'}
CID=os.getenv('GOOGLE_CLIENT_ID',''); SECRET=os.getenv('GOOGLE_CLIENT_SECRET',''); CALLBACK=os.getenv('GOOGLE_REDIRECT_URI','https://thienha.io.vn/auth/callback')
app=Flask(__name__); app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=1)
app.secret_key=os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_SECURE=True,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=128*1024*1024)

TEXT={'vi':{'home':'Trang chủ','projects':'Dự án','firmware':'Firmware','account':'Tài khoản','admin':'Quản trị','signin':'Đăng nhập','signout':'Đăng xuất','hero_tag':'SOFTWARE · EMBEDDED · OPEN ENGINEERING','hero':'Xây dựng. Kiểm chứng. Chia sẻ.','hero_desc':'Không gian kỹ thuật cá nhân dành cho dự án phần mềm, hệ thống nhúng, mã nguồn và firmware được phát hành có kiểm soát.','explore':'Khám phá dự án','repository':'Kho phát hành','principles':'Nguyên tắc vận hành','clear':'Thông tin kỹ thuật rõ ràng','clear_d':'Phiên bản, thiết bị hỗ trợ, checksum và thời hạn được công bố trước khi tải.','roles':'Phân quyền tại backend','roles_d':'Thành viên chỉ xem và tải. Chỉ quản trị viên được tạo, sửa, tải lên hoặc gỡ nội dung.','controlled':'Phát hành có kiểm soát','controlled_d':'Tệp nằm ngoài thư mục public và chỉ được phân phối sau khi kiểm tra quyền và thời hạn.','catalog':'Danh mục kỹ thuật','catalog_d':'Mã nguồn, tài liệu và firmware được tổ chức theo dự án và phiên bản.','active':'Đang mở','expired':'Hết hạn','draft':'Bản nháp','view':'Xem chi tiết','empty':'Chưa có dự án được công bố.','overview':'Tổng quan','files':'Tệp phát hành','download':'Tải xuống','login_download':'Đăng nhập để tải','expires':'Hết hạn','version':'Phiên bản','size':'Dung lượng','checksum':'SHA-256','no_files':'Chưa có tệp phát hành.','firmware_h':'Kho firmware','firmware_d':'Chọn dự án và tải firmware đã được quản trị viên kiểm chứng. Website không ghi trực tiếp vào USB/COM.','source':'Mã nguồn','document':'Tài liệu','profile':'Hồ sơ người dùng','role':'Vai trò','member':'Thành viên','administrator':'Quản trị viên','status':'Trạng thái','last_login':'Đăng nhập gần nhất','manage':'Quản lý nội dung','admin_h':'Bảng điều khiển quản trị','admin_d':'Tạo, cập nhật và xóa dự án, firmware, mã nguồn và tài liệu.','new':'Tạo dự án','edit':'Chỉnh sửa','delete':'Xóa','users':'Người dùng','created':'Ngày tạo','save':'Lưu thay đổi','upload':'Tải tệp lên','kind':'Phân loại','file':'Tệp','title_vi':'Tên tiếng Việt','title_en':'Tên tiếng Anh','summary_vi':'Mô tả ngắn tiếng Việt','summary_en':'Mô tả ngắn tiếng Anh','body_vi':'Nội dung tiếng Việt','body_en':'Nội dung tiếng Anh','slug':'Đường dẫn','project_status':'Trạng thái dự án','confirm':'Bạn chắc chắn muốn xóa?','all':'Tất cả','category':'Phân loại','standard':'Tiêu chuẩn','experimental_training':'Thử nghiệm & Đào tạo'},
'en':{'home':'Home','projects':'Projects','firmware':'Firmware','account':'Account','admin':'Admin','signin':'Sign in','signout':'Sign out','hero_tag':'SOFTWARE · EMBEDDED · OPEN ENGINEERING','hero':'Build. Validate. Share.','hero_desc':'A personal engineering space for software, embedded systems, source code and controlled firmware releases.','explore':'Explore projects','repository':'Release repository','principles':'Operating principles','clear':'Clear technical information','clear_d':'Versions, supported hardware, checksums and availability windows are published before download.','roles':'Backend authorization','roles_d':'Members can view and download. Only the administrator can create, edit, upload or remove content.','controlled':'Controlled releases','controlled_d':'Files remain outside the public directory and are served only after access and expiry checks.','catalog':'Engineering catalog','catalog_d':'Source code, documentation and firmware organized by project and version.','active':'Available','expired':'Expired','draft':'Draft','view':'View details','empty':'No projects have been published.','overview':'Overview','files':'Release files','download':'Download','login_download':'Sign in to download','expires':'Expires','version':'Version','size':'Size','checksum':'SHA-256','no_files':'No release files yet.','firmware_h':'Firmware repository','firmware_d':'Select a project and download administrator-verified firmware. The website does not flash USB/COM devices.','source':'Source code','document':'Documentation','profile':'User profile','role':'Role','member':'Member','administrator':'Administrator','status':'Status','last_login':'Last sign-in','manage':'Manage content','admin_h':'Administration console','admin_d':'Create, update and delete projects, firmware, source code and documentation.','new':'Create project','edit':'Edit','delete':'Delete','users':'Users','created':'Created','save':'Save changes','upload':'Upload file','kind':'Type','file':'File','title_vi':'Vietnamese title','title_en':'English title','summary_vi':'Vietnamese summary','summary_en':'English summary','body_vi':'Vietnamese content','body_en':'English content','slug':'URL slug','project_status':'Project status','confirm':'Are you sure you want to delete this?','all':'All','category':'Category','standard':'Standard','experimental_training':'Experimental & Training','education_training':'Giáo dục – Đào tạo','engineering_technology':'Kỹ thuật – Công nghệ','entertainment_games':'Giải trí – Trò chơi','business_commerce':'Kinh doanh – Mua bán','support_other':'Hỗ trợ – Khác'}}

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def now(): return datetime.now(timezone.utc).isoformat()
def init():
 DATA.mkdir(parents=True,exist_ok=True); FILES.mkdir(exist_ok=True)
 with db() as c:c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,google_sub TEXT UNIQUE,email TEXT UNIQUE COLLATE NOCASE,name TEXT NOT NULL DEFAULT '',picture TEXT NOT NULL DEFAULT '',role TEXT NOT NULL DEFAULT 'member',status TEXT NOT NULL DEFAULT 'active',created_at TEXT NOT NULL,last_login_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT,slug TEXT UNIQUE NOT NULL,title_vi TEXT NOT NULL,title_en TEXT NOT NULL,summary_vi TEXT NOT NULL DEFAULT '',summary_en TEXT NOT NULL DEFAULT '',body_vi TEXT NOT NULL DEFAULT '',body_en TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'draft',category TEXT NOT NULL DEFAULT 'standard',expires_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS releases(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,name TEXT NOT NULL,stored_name TEXT NOT NULL,kind TEXT NOT NULL,version TEXT NOT NULL DEFAULT '',size INTEGER NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY AUTOINCREMENT,name_vi TEXT NOT NULL,name_en TEXT NOT NULL,summary_vi TEXT NOT NULL DEFAULT '',summary_en TEXT NOT NULL DEFAULT '',kind TEXT NOT NULL,version TEXT NOT NULL DEFAULT '',access TEXT NOT NULL DEFAULT 'free',demo_file TEXT,full_file TEXT,price INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS entitlements(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),asset_id INTEGER NOT NULL REFERENCES assets(id),granted_at TEXT NOT NULL,UNIQUE(user_id,asset_id));CREATE TABLE IF NOT EXISTS payment_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),asset_id INTEGER REFERENCES assets(id),purpose TEXT NOT NULL,amount INTEGER NOT NULL,reference TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,reviewed_at TEXT);CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),item_type TEXT NOT NULL,item_id INTEGER NOT NULL,item_name TEXT NOT NULL,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL DEFAULT '');""")
init()
with db() as c:
 cols={x['name'] for x in c.execute('PRAGMA table_info(projects)')}
 if 'category' not in cols: c.execute("ALTER TABLE projects ADD COLUMN category TEXT NOT NULL DEFAULT 'standard'")
 if 'host_url' not in cols: c.execute("ALTER TABLE projects ADD COLUMN host_url TEXT NOT NULL DEFAULT ''")
 for name,definition in {
  'cover_url':"TEXT NOT NULL DEFAULT ''",'accent':"TEXT NOT NULL DEFAULT '#4bdbe4'",
  'tags':"TEXT NOT NULL DEFAULT ''",'repo_url':"TEXT NOT NULL DEFAULT ''",
  'docs_url':"TEXT NOT NULL DEFAULT ''",'featured':"INTEGER NOT NULL DEFAULT 0",
  'sort_order':"INTEGER NOT NULL DEFAULT 0",'content_json':"TEXT NOT NULL DEFAULT '[]'",
  'gallery_json':"TEXT NOT NULL DEFAULT '[]'",'seo_title':"TEXT NOT NULL DEFAULT ''",
  'seo_description':"TEXT NOT NULL DEFAULT ''"
 }.items():
  if name not in cols: c.execute(f"ALTER TABLE projects ADD COLUMN {name} {definition}")
 pay_cols={x['name'] for x in c.execute('PRAGMA table_info(payment_requests)')}
 for name,definition in {
  'service_name':"TEXT NOT NULL DEFAULT ''",
  'mac_address':"TEXT NOT NULL DEFAULT ''",
  'duration_days':"INTEGER NOT NULL DEFAULT 0"
 }.items():
  if name not in pay_cols: c.execute(f"ALTER TABLE payment_requests ADD COLUMN {name} {definition}")
 asset_cols={x['name'] for x in c.execute('PRAGMA table_info(assets)')}
 if 'install_manifest' not in asset_cols: c.execute("ALTER TABLE assets ADD COLUMN install_manifest TEXT NOT NULL DEFAULT ''")
 c.execute("CREATE TABLE IF NOT EXISTS admin_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,admin_user_id INTEGER,user_id INTEGER,action TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL)")
 c.execute("CREATE TABLE IF NOT EXISTS page_revisions(id INTEGER PRIMARY KEY AUTOINCREMENT,page_slug TEXT NOT NULL,content_html TEXT NOT NULL,created_by INTEGER,created_at TEXT NOT NULL)")
 c.execute("""CREATE TABLE IF NOT EXISTS service_catalog(
  service_name TEXT PRIMARY KEY, display_name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  price_month INTEGER NOT NULL DEFAULT 10000, price_year INTEGER NOT NULL DEFAULT 50000,
  price_lifetime INTEGER NOT NULL DEFAULT 150000, enabled INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)""")
 c.execute("""CREATE TABLE IF NOT EXISTS service_order_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, payment_request_id INTEGER NOT NULL REFERENCES payment_requests(id) ON DELETE CASCADE,
  service_name TEXT NOT NULL, mac_address TEXT NOT NULL, billing_period TEXT NOT NULL,
  unit_price INTEGER NOT NULL, duration_days INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""")
 c.execute("""CREATE TABLE IF NOT EXISTS project_service_catalog(
  service_name TEXT PRIMARY KEY, display_name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  price_month INTEGER NOT NULL DEFAULT 30000, price_year INTEGER NOT NULL DEFAULT 300000,
  price_lifetime INTEGER NOT NULL DEFAULT 1000000, enabled INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)""")
 c.execute("""CREATE TABLE IF NOT EXISTS account_project_licenses(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  service_name TEXT NOT NULL REFERENCES project_service_catalog(service_name),
  expires_at TEXT, enabled INTEGER NOT NULL DEFAULT 1,
  activated_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  PRIMARY KEY(user_id, service_name))""")
 c.execute("INSERT OR IGNORE INTO project_service_catalog(service_name,display_name,description,price_month,price_year,price_lifetime,enabled,sort_order,updated_at) VALUES('game-of-thien','Game of Thiên · Học qua chơi','Nền tảng học tập cho mẫu giáo và tiểu học; quản lý phiên và giới hạn thời lượng.',30000,300000,1000000,1,10,?)",(now(),))
 c.execute("DELETE FROM service_catalog WHERE service_name='game-of-thien'")
 from xiaozhi_tools import TOOLS
 for position,(service_name,description) in enumerate(TOOLS.items()):
  c.execute("INSERT OR IGNORE INTO service_catalog(service_name,display_name,description,price_month,price_year,price_lifetime,enabled,sort_order,updated_at) VALUES(?,?,?,10000,50000,150000,1,?,?)",(service_name,service_name,description,position,now()))


def service_catalog(include_disabled=False):
 with db() as c:
  sql='SELECT * FROM service_catalog' + ('' if include_disabled else ' WHERE enabled=1') + ' ORDER BY sort_order,display_name'
  return [dict(row) for row in c.execute(sql)]

def subscription_expiry(current, period):
 if period=='lifetime': return '9999-12-31T23:59:59+00:00'
 start=datetime.now(timezone.utc)
 try:
  old=datetime.fromisoformat(current or '')
  if old.tzinfo is None:old=old.replace(tzinfo=timezone.utc)
  if old>start:start=old
 except (TypeError,ValueError):pass
 return (start+timedelta(days=30 if period=='month' else 365)).isoformat(timespec='seconds')
def language():
 return 'vi'
def current_user():
 if not session.get('uid'): return None
 with db() as c:r=c.execute('SELECT * FROM users WHERE id=?',(session['uid'],)).fetchone()
 return dict(r) if r and r['status']=='active' else None
def is_admin(u=None): u=u or current_user(); return bool(u and u['email'].lower()==ADMIN and u['role']=='admin')
def csrf():
 if not session.get('csrf'): session['csrf']=secrets.token_urlsafe(32)
 return session['csrf']
def check_csrf():
 if not secrets.compare_digest(request.form.get('csrf',''),session.get('csrf','')): abort(400)
def admin_only(f):
 @wraps(f)
 def w(*a,**k):
  if not current_user(): return redirect(url_for('login',next=request.path))
  if not is_admin(): abort(403)
  return f(*a,**k)
 return w
@app.context_processor
def context(): return {'L':TEXT[language()],'lang':language(),'me':current_user(),'admin_user':is_admin(),'csrf_token':csrf()}
@app.after_request
def secure(r):
 r.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'strict-origin-when-cross-origin','Permissions-Policy':'camera=(), microphone=(), geolocation=()','Strict-Transport-Security':'max-age=31536000; includeSubDomains'})
 return r
@app.get('/language/<code>')
def set_language(code):
 return redirect(request.referrer or '/')
@app.get('/')
def home():
 if request.host.split(':',1)[0].lower()=='gameofthien.thienha.io.vn':
  token=request.args.get('session','').strip()
  if len(token)<32 or len(token)>96:return render_template('game_session.html',session_error='Phiên học không tồn tại hoặc chưa được cấp.',game_config=None),404
  with db() as c:
   row=c.execute('SELECT * FROM game_sessions WHERE token=?',(token,)).fetchone()
   if not row:return render_template('game_session.html',session_error='Phiên học không tồn tại hoặc chưa được cấp.',game_config=None),404
   try: expires=datetime.fromisoformat(row['expires_at'])
   except (TypeError,ValueError): expires=datetime.now(timezone.utc)-timedelta(seconds=1)
   if expires.tzinfo is None:expires=expires.replace(tzinfo=timezone.utc)
   if expires<=datetime.now(timezone.utc) or row['status'] not in ('ready','started'):
    return render_template('game_session.html',session_error='Phiên học đã hết hạn. Người lớn cần mở một phiên mới.',game_config=None),410
   started=row['started_at'] or now()
   if row['status']=='ready':c.execute("UPDATE game_sessions SET status='started',started_at=? WHERE id=?",(started,row['id']))
  return render_template('game_session.html',session_error=None,game_config=json.loads(row['config_json']),session_expires=row['expires_at'],session_token=token)
 with db() as c:items=c.execute("SELECT * FROM projects WHERE status='active' ORDER BY featured DESC,sort_order ASC,updated_at DESC LIMIT 6").fetchall()
 return render_template('home.html',items=items)
@app.get('/projects')
def projects():
 with db() as c:items=c.execute("SELECT * FROM projects WHERE status!='draft' OR ? ORDER BY featured DESC,sort_order ASC,updated_at DESC",(1 if is_admin() else 0,)).fetchall()
 return render_template('projects.html',items=items)
@app.get('/projects/<slug>')
def project(slug):
 with db() as c:
  p=c.execute('SELECT * FROM projects WHERE slug=?',(slug,)).fetchone()
  if not p or (p['status']=='draft' and not is_admin()): abort(404)
  releases=c.execute('SELECT * FROM releases WHERE project_id=? ORDER BY created_at DESC',(p['id'],)).fetchall()
 try: content=json.loads(p['content_json'] or '[]'); gallery=json.loads(p['gallery_json'] or '[]')
 except (ValueError,TypeError): content=[]; gallery=[]
 return render_template('project.html',p=p,releases=releases,content=content,gallery=gallery,tags=[x.strip() for x in (p['tags'] or '').split(',') if x.strip()])
@app.get('/firmware')
def firmware():
 with db() as c:items=c.execute("SELECT r.*,p.slug,p.title_vi,p.title_en,p.expires_at FROM releases r JOIN projects p ON p.id=r.project_id WHERE r.kind='firmware' AND p.status='active' ORDER BY r.created_at DESC").fetchall()
 return render_template('firmware.html',items=items)
@app.get('/download/<int:rid>')
def download(rid):
 if not current_user(): return redirect(url_for('login',next=request.path))
 with db() as c:r=c.execute('SELECT r.*,p.status,p.expires_at FROM releases r JOIN projects p ON p.id=r.project_id WHERE r.id=?',(rid,)).fetchone()
 if not r or (r['status']!='active' and not is_admin()): abort(404)
 if r['expires_at'] and r['expires_at']<now() and not is_admin(): abort(410)
 return send_file(FILES/r['stored_name'],as_attachment=True,download_name=r['name'])
@app.get('/account')
def account():
 u=current_user(); activities=[]; entitlements=[]; payments=[]
 if u:
  with db() as c:
   activities=c.execute('SELECT * FROM activity WHERE user_id=? ORDER BY created_at DESC LIMIT 30',(u['id'],)).fetchall(); entitlements=c.execute('SELECT a.* FROM entitlements e JOIN assets a ON a.id=e.asset_id WHERE e.user_id=?',(u['id'],)).fetchall(); payments=c.execute('SELECT p.*,a.name_vi,a.name_en FROM payment_requests p LEFT JOIN assets a ON a.id=p.asset_id WHERE p.user_id=? ORDER BY p.created_at DESC',(u['id'],)).fetchall()
 return render_template('account.html',activities=activities,entitlements=entitlements,payments=payments)
@app.get('/login')
def login():
 state=secrets.token_urlsafe(32); session['oauth_state']=state; session['next']=request.args.get('next','/')
 q=urllib.parse.urlencode({'client_id':CID,'redirect_uri':CALLBACK,'response_type':'code','scope':'openid email profile','state':state,'prompt':'select_account'}); return redirect('https://accounts.google.com/o/oauth2/v2/auth?'+q)
@app.get('/auth/callback')
def callback():
 if request.args.get('state')!=session.pop('oauth_state',None): abort(400)
 data=urllib.parse.urlencode({'code':request.args.get('code'),'client_id':CID,'client_secret':SECRET,'redirect_uri':CALLBACK,'grant_type':'authorization_code'}).encode()
 with urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=data),timeout=15) as x:token=json.load(x)
 with urllib.request.urlopen('https://oauth2.googleapis.com/tokeninfo?id_token='+urllib.parse.quote(token['id_token']),timeout=15) as x:i=json.load(x)
 if i.get('aud')!=CID or str(i.get('email_verified','')).lower()!='true': abort(403)
 email=i['email'].lower(); role='admin' if email==ADMIN else 'member'; stamp=now()
 with db() as c:
  c.execute("INSERT INTO users(google_sub,email,name,picture,role,status,created_at,last_login_at) VALUES(?,?,?,?,?,'active',?,?) ON CONFLICT(email) DO UPDATE SET name=excluded.name,picture=excluded.picture,role=excluded.role,last_login_at=excluded.last_login_at",(i['sub'],email,i.get('name',''),i.get('picture',''),role,stamp,stamp)); uid=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']
 session['uid']=uid; return redirect(session.pop('next','/'))
@app.after_request
def ensure_game_trial_after_login(response):
 u=current_user()
 if u:
  stamp=now(); trial_expires=(datetime.now(timezone.utc).astimezone()+timedelta(days=7)).isoformat(timespec='seconds')
  with db() as c:c.execute("INSERT OR IGNORE INTO account_project_licenses(user_id,service_name,expires_at,enabled,activated_at,updated_at) VALUES(?,'game-of-thien',?,1,?,?)",(u['id'],trial_expires,stamp,stamp))
 return response

@app.post('/logout')
def logout(): session.clear(); return redirect('/')
@app.get('/admin')
@admin_only
def admin():
 with db() as c:items=c.execute('SELECT * FROM projects ORDER BY featured DESC,sort_order ASC,updated_at DESC').fetchall(); users=c.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()

 with db() as c: assets=c.execute('SELECT * FROM assets ORDER BY created_at DESC').fetchall(); payments=c.execute('SELECT p.*,u.email,a.name_vi,a.name_en FROM payment_requests p JOIN users u ON u.id=p.user_id LEFT JOIN assets a ON a.id=p.asset_id ORDER BY p.created_at DESC').fetchall(); settings={r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}
 return render_template('admin.html',items=items,users=users,assets=assets,payments=payments,settings=settings)

@app.get('/admin/devices')
@admin_only
def admin_devices_page():
 return render_template('admin_devices.html')
@app.route('/admin/projects/new',methods=['GET','POST'])
@app.route('/admin/projects/<int:pid>',methods=['GET','POST'])
@admin_only
def edit_project(pid=None):
 p=None
 if pid:
  with db() as c:p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
 if request.method=='POST':
  check_csrf()
  slug=request.form.get('slug','').strip().lower(); slug=re.sub(r'[^a-z0-9-]+','-',slug).strip('-')
  if not slug: abort(400)
  content_raw=request.form.get('content_json','[]'); gallery_raw=request.form.get('gallery_json','[]')
  try:
   content=json.loads(content_raw); gallery=json.loads(gallery_raw)
   if not isinstance(content,list) or not isinstance(gallery,list): raise ValueError()
  except (ValueError,TypeError,json.JSONDecodeError): abort(400)
  keys=('title_vi','title_en','summary_vi','summary_en','body_vi','body_en','status','category','host_url','cover_url','accent','tags','repo_url','docs_url','seo_title','seo_description')
  v=[request.form.get(x,'').strip() for x in keys]
  if not v[1]: v[1]=v[0]
  if not v[3]: v[3]=v[2]
  if not v[5]: v[5]=v[4]
  featured=1 if request.form.get('featured')=='1' else 0
  try: sort_order=int(request.form.get('sort_order','0'))
  except ValueError: sort_order=0
  expires=request.form.get('expires_at','').strip() or None; stamp=now(); packed=json.dumps(content,ensure_ascii=False); packed_gallery=json.dumps(gallery,ensure_ascii=False)
  with db() as c:
   values=(slug,*v,featured,sort_order,packed,packed_gallery,expires,stamp)
   if pid:c.execute('UPDATE projects SET slug=?,title_vi=?,title_en=?,summary_vi=?,summary_en=?,body_vi=?,body_en=?,status=?,category=?,host_url=?,cover_url=?,accent=?,tags=?,repo_url=?,docs_url=?,seo_title=?,seo_description=?,featured=?,sort_order=?,content_json=?,gallery_json=?,expires_at=?,updated_at=? WHERE id=?',(*values,pid))
   else:c.execute('INSERT INTO projects(slug,title_vi,title_en,summary_vi,summary_en,body_vi,body_en,status,category,host_url,cover_url,accent,tags,repo_url,docs_url,seo_title,seo_description,featured,sort_order,content_json,gallery_json,expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*values,stamp)); pid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
  return redirect(url_for('edit_project',pid=pid))
 with db() as c:releases=c.execute('SELECT * FROM releases WHERE project_id=?',(pid or 0,)).fetchall()
 return render_template('edit.html',p=p,releases=releases)

@app.get('/admin/projects/<int:pid>/preview')
@admin_only
def preview_project(pid):
 with db() as c:
  p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone(); releases=c.execute('SELECT * FROM releases WHERE project_id=? ORDER BY created_at DESC',(pid,)).fetchall()
 if not p: abort(404)
 try: content=json.loads(p['content_json'] or '[]'); gallery=json.loads(p['gallery_json'] or '[]')
 except (ValueError,TypeError): content=[]; gallery=[]
 return render_template('project.html',p=p,releases=releases,content=content,gallery=gallery,tags=[x.strip() for x in (p['tags'] or '').split(',') if x.strip()],preview=True)
@app.post('/admin/projects/<int:pid>/upload')
@admin_only
def upload(pid):
 check_csrf()
 f=request.files.get('file'); name=secure_filename(f.filename) if f else ''; ext=Path(name).suffix.lower()
 if not f or ext not in ALLOWED: abort(400)
 stored=uuid.uuid4().hex+ext; path=FILES/stored; f.save(path); digest=hashlib.sha256(path.read_bytes()).hexdigest()
 with db() as c:c.execute('INSERT INTO releases(project_id,name,stored_name,kind,version,size,sha256,created_at) VALUES(?,?,?,?,?,?,?,?)',(pid,name,stored,request.form['kind'],request.form.get('version',''),path.stat().st_size,digest,now()))
 return redirect(url_for('edit_project',pid=pid))
@app.post('/admin/projects/<int:pid>/delete')
@admin_only
def remove_project(pid):
 check_csrf()
 with db() as c:names=[x['stored_name'] for x in c.execute('SELECT stored_name FROM releases WHERE project_id=?',(pid,))]; c.execute('DELETE FROM projects WHERE id=?',(pid,))
 for n in names:(FILES/n).unlink(missing_ok=True)
 return redirect('/admin')
@app.post('/admin/releases/<int:rid>/delete')
@admin_only
def remove_release(rid):
 check_csrf()
 with db() as c:r=c.execute('SELECT * FROM releases WHERE id=?',(rid,)).fetchone(); c.execute('DELETE FROM releases WHERE id=?',(rid,))
 if not r: abort(404)
 (FILES/r['stored_name']).unlink(missing_ok=True); return redirect(url_for('edit_project',pid=r['project_id']))

@app.get('/downloads')
def downloads():
 with db() as c: items=c.execute('SELECT * FROM assets ORDER BY kind,name_vi').fetchall()
 return render_template('downloads.html',items=items)
@app.get('/asset/<int:aid>/download/<tier>')
def asset_download(aid,tier):
 u=current_user()
 if not u:return redirect(url_for('login',next=request.path))
 with db() as c:
  a=c.execute('SELECT * FROM assets WHERE id=?',(aid,)).fetchone()
  if not a:abort(404)
  if tier=='full' and a['access']=='paid' and not is_admin(u) and not c.execute('SELECT 1 FROM entitlements WHERE user_id=? AND asset_id=?',(u['id'],aid)).fetchone():abort(403)
  stored=a['full_file'] if tier=='full' else a['demo_file']
  if not stored:abort(404)
  c.execute('INSERT INTO activity(user_id,item_type,item_id,item_name,created_at) VALUES(?,?,?,?,?)',(u['id'],a['kind'],aid,a['name_vi'],now()))
 return send_file(FILES/stored,as_attachment=True,download_name=stored.split('_',1)[-1])
@app.post('/unlock/<int:aid>')
def unlock(aid):
 u=current_user()
 if not u:return redirect(url_for('login',next=request.path))
 check_csrf()
 with db() as c:
  a=c.execute('SELECT * FROM assets WHERE id=?',(aid,)).fetchone()
  if not a:abort(404)
  ref=request.form.get('reference','').strip()
  if not ref:abort(400)
  c.execute("INSERT INTO payment_requests(user_id,asset_id,purpose,amount,reference,status,created_at) VALUES(?,?,?,?,?,'pending',?)",(u['id'],aid,'unlock',a['price'],ref,now()))
 return redirect('/account')
@app.post('/donate')
def donate():
 u=current_user()
 if not u:return redirect(url_for('login',next=request.path))
 check_csrf(); amount=int(request.form.get('amount','0')); ref=request.form.get('reference','').strip()
 if amount<1000 or not ref:abort(400)
 with db() as c:c.execute("INSERT INTO payment_requests(user_id,purpose,amount,reference,status,created_at) VALUES(?,'donate',?,?, 'pending',?)",(u['id'],amount,ref,now()))
 return redirect('/account')
@app.post('/activate-service')
def activate_service_request():
 u=current_user()
 if not u:return redirect(url_for('login',next='/support'))
 check_csrf()
 from xiaozhi_tools import TOOLS, _normalize_mac
 service=request.form.get('service_name','').strip(); mac=_normalize_mac(request.form.get('mac_address',''))
 reference=request.form.get('reference','').strip()[:120]
 if service not in TOOLS or not mac or not reference:abort(400)
 with db() as c:
  if not c.execute('SELECT 1 FROM robot_bindings WHERE user_id=? AND mac_address=?',(u['id'],mac)).fetchone():abort(403)
  c.execute("INSERT INTO payment_requests(user_id,purpose,amount,reference,status,created_at,service_name,mac_address,duration_days) VALUES(?,'service_activation',50000,?,'pending',?,?,?,365)",(u['id'],reference,now(),service,mac))
 return redirect('/account')
@app.post('/purchase-services')
def purchase_services():
 u=current_user()
 if not u:return redirect(url_for('login',next='/support'))
 check_csrf(); reference=request.form.get('reference','').strip()[:120]
 try: raw=json.loads(request.form.get('items','[]'))
 except (ValueError,TypeError):abort(400)
 if not reference or not isinstance(raw,list) or not raw or len(raw)>50:abort(400)
 catalog={row['service_name']:row for row in service_catalog()}
 with db() as c:
  game_row=c.execute("SELECT * FROM project_service_catalog WHERE service_name='game-of-thien' AND enabled=1").fetchone()
 if game_row: catalog['game-of-thien']=game_row
 clean=[]; total=0
 with db() as c:
  owned={row['mac_address'] for row in c.execute('SELECT mac_address FROM robot_bindings WHERE user_id=?',(u['id'],))}
  for item in raw:
   from xiaozhi_tools import _normalize_mac
   name=str(item.get('service_name','')); period=str(item.get('billing_period','year')); raw_mac=str(item.get('mac_address','')); mac='ACCOUNT' if name=='game-of-thien' else _normalize_mac(raw_mac)
   if name not in catalog or period not in ('month','year','lifetime') or (name!='game-of-thien' and mac not in owned):abort(400)
   price=int(catalog[name]['price_'+period]); days={'month':30,'year':365,'lifetime':0}[period]
   clean.append((name,mac,period,price,days)); total+=price
  if total<=0:abort(400)
  c.execute("INSERT INTO payment_requests(user_id,purpose,amount,reference,status,created_at) VALUES(?,'service_bundle',?,?,'pending',?)",(u['id'],total,reference,now()))
  payment_id=c.execute('SELECT last_insert_rowid()').fetchone()[0]
  c.executemany('INSERT INTO service_order_items(payment_request_id,service_name,mac_address,billing_period,unit_price,duration_days,created_at) VALUES(?,?,?,?,?,?,?)',[(payment_id,*item,now()) for item in clean])
 return redirect('/account')

@app.post('/purchase-commerce')
def purchase_commerce():
 u=current_user()
 if not u:return redirect(url_for('login',next='/support'))
 check_csrf(); reference=request.form.get('reference','').strip()[:120]
 try: items=json.loads(request.form.get('items','[]'))
 except (TypeError,ValueError):abort(400)
 if not reference or not isinstance(items,list) or not 1<=len(items)<=30:abort(400)
 clean=[];total=0
 with db() as c:
  owned={r['mac_address'] for r in c.execute('SELECT mac_address FROM robot_bindings WHERE user_id=?',(u['id'],))}
  for raw in items:
   offer=c.execute('SELECT * FROM commercial_offers WHERE id=? AND enabled=1',(int(raw.get('offer_id',0)),)).fetchone()
   period=str(raw.get('period','year')); hardware=str(raw.get('hardware','')).strip()
   if not offer or period not in ('month','year','lifetime'):abort(400)
   if offer['requires_hardware'] and hardware not in owned:abort(403)
   if not offer['requires_hardware']:hardware=''
   price=int(offer['price_'+period]);days={'month':30,'year':365,'lifetime':0}[period]
   clean.append((offer['id'],period,hardware,price,days));total+=price
  if total<=0:abort(400)
  c.execute("INSERT INTO payment_requests(user_id,purpose,amount,reference,status,created_at) VALUES(?,'commercial_order',?,?,'pending',?)",(u['id'],total,reference,now()))
  pid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
  c.executemany('INSERT INTO commercial_order_items(payment_request_id,offer_id,billing_period,hardware_key,unit_price,duration_days,created_at) VALUES(?,?,?,?,?,?,?)',[(pid,*x,now()) for x in clean])
 return redirect('/account')

@app.post('/commercial/cancel')
def cancel_commercial():
 u=current_user()
 if not u:return redirect(url_for('login',next='/support'))
 check_csrf();offer_id=int(request.form.get('offer_id','0'))
 with db() as c:
  offer=c.execute("SELECT * FROM commercial_offers WHERE id=? AND cancelable=1",(offer_id,)).fetchone()
  if offer:
   hardware=request.args.get('hardware_key',request.form.get('hardware_key','')).strip()
   c.execute("UPDATE user_commercial_entitlements SET enabled=0,updated_at=? WHERE user_id=? AND offer_id=? AND hardware_key=?",(now(),u['id'],offer_id,hardware))
   if offer['offer_key']=='game-of-thien':
    c.execute("UPDATE account_project_licenses SET enabled=0,updated_at=? WHERE user_id=? AND service_name='game-of-thien'",(now(),u['id']))
   elif offer['requires_hardware']:
    c.execute("UPDATE mac_tool_licenses SET enabled=0 WHERE user_id=? AND mac_address=? AND tool_name=?",(u['id'],hardware,offer['offer_key']))
 return redirect('/support')

@app.get('/support')
def support():
 devices=[]
 with db() as c:
  settings={r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}
  u=current_user()
  if u: devices=c.execute('SELECT session_id,mac_address FROM robot_bindings WHERE user_id=? ORDER BY created_at DESC',(u['id'],)).fetchall()

 with db() as c: game_service=c.execute("SELECT * FROM project_service_catalog WHERE service_name='game-of-thien' AND enabled=1").fetchone()
 with db() as c:
  commerce_projects=c.execute("SELECT DISTINCT p.* FROM projects p JOIN commercial_offers o ON o.project_id=p.id WHERE o.enabled=1 AND p.status='active' ORDER BY p.sort_order,p.title_vi").fetchall()
  commerce_offers=c.execute("SELECT o.*,p.title_vi project_title FROM commercial_offers o JOIN projects p ON p.id=o.project_id WHERE o.enabled=1 ORDER BY p.sort_order,o.sort_order,o.display_name").fetchall()
  entitlements=[]
  if u: entitlements=c.execute("SELECT e.*,o.id offer_id,o.display_name,o.cancelable,p.title_vi project_title FROM user_commercial_entitlements e JOIN commercial_offers o ON o.id=e.offer_id JOIN projects p ON p.id=o.project_id WHERE e.user_id=? AND e.enabled=1 ORDER BY p.title_vi,o.display_name",(u['id'],)).fetchall()
 return render_template('support.html',settings=settings,devices=devices,commerce_projects=commerce_projects,commerce_offers=commerce_offers,entitlements=entitlements,project_type_labels={'education_training':'Giáo dục – Đào tạo','engineering_technology':'Kỹ thuật – Công nghệ','entertainment_games':'Giải trí – Trò chơi','business_commerce':'Kinh doanh – Mua bán','support_other':'Hỗ trợ – Khác'})

@app.post('/admin/services/save')
@admin_only
def admin_service_save():
 check_csrf(); name=re.sub(r'[^a-z0-9_]+','_',request.form.get('service_name','').strip().lower()).strip('_')[:64]
 if not name:abort(400)
 try: prices=[max(0,int(request.form.get(key,'0'))) for key in ('price_month','price_year','price_lifetime')]; order=int(request.form.get('sort_order','0'))
 except ValueError:abort(400)
 with db() as c:c.execute("INSERT INTO service_catalog(service_name,display_name,description,price_month,price_year,price_lifetime,enabled,sort_order,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(service_name) DO UPDATE SET display_name=excluded.display_name,description=excluded.description,price_month=excluded.price_month,price_year=excluded.price_year,price_lifetime=excluded.price_lifetime,enabled=excluded.enabled,sort_order=excluded.sort_order,updated_at=excluded.updated_at",(name,request.form.get('display_name','').strip() or name,request.form.get('description','').strip(),*prices,1 if request.form.get('enabled')=='1' else 0,order,now()))
 return redirect('/admin/devices')
@app.get('/account/history')
def account_history():return redirect('/account')
@app.post('/admin/assets/new')
@admin_only
def asset_new():
 check_csrf(); demo=request.files.get('demo'); full=request.files.get('full')
 def saveup(f):
  if not f or not f.filename:return None
  n=secure_filename(f.filename); ext=Path(n).suffix.lower()
  if ext not in ALLOWED:abort(400)
  s=uuid.uuid4().hex+'_'+n; f.save(FILES/s); return s
 d=saveup(demo); f=saveup(full)
 with db() as c:c.execute('INSERT INTO assets(name_vi,name_en,summary_vi,summary_en,kind,version,access,demo_file,full_file,price,created_at,install_manifest) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(request.form['name_vi'],request.form['name_en'],request.form.get('summary_vi',''),request.form.get('summary_en',''),request.form['kind'],request.form.get('version',''),request.form['access'],d,f,int(request.form.get('price','0')),now(),request.form.get('install_manifest','').strip()))
 return redirect('/admin')
@app.post('/admin/payments/<int:pid>/<decision>')
@admin_only
def payment_review(pid,decision):
 check_csrf()
 if decision not in ('approved','rejected'):abort(400)
 with db() as c:
  p=c.execute('SELECT * FROM payment_requests WHERE id=?',(pid,)).fetchone()
  if not p:abort(404)
  c.execute('UPDATE payment_requests SET status=?,reviewed_at=? WHERE id=?',(decision,now(),pid))
  if decision=='approved' and p['asset_id']:c.execute('INSERT OR IGNORE INTO entitlements(user_id,asset_id,granted_at) VALUES(?,?,?)',(p['user_id'],p['asset_id'],now()))
  if decision=='approved' and p['purpose']=='service_bundle':
   items=c.execute('SELECT * FROM service_order_items WHERE payment_request_id=?',(pid,)).fetchall()
   for item in items:
    if item['service_name']=='game-of-thien':
     current=c.execute("SELECT expires_at FROM account_project_licenses WHERE user_id=? AND service_name='game-of-thien'",(p['user_id'],)).fetchone()
     expires=subscription_expiry(current['expires_at'] if current else None,item['billing_period'])
     c.execute("INSERT INTO account_project_licenses(user_id,service_name,expires_at,enabled,activated_at,updated_at) VALUES(?,'game-of-thien',?,1,?,?) ON CONFLICT(user_id,service_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=1,updated_at=excluded.updated_at",(p['user_id'],expires,now(),now()))
    else:
     current=c.execute('SELECT expires_at FROM mac_tool_licenses WHERE user_id=? AND mac_address=? AND tool_name=?',(p['user_id'],item['mac_address'],item['service_name'])).fetchone()
     expires=subscription_expiry(current['expires_at'] if current else None,item['billing_period'])
     c.execute('INSERT OR IGNORE INTO mac_service_profiles(user_id,mac_address,created_at) VALUES(?,?,?)',(p['user_id'],item['mac_address'],now()))
     c.execute('INSERT INTO mac_tool_licenses(user_id,mac_address,tool_name,expires_at,enabled) VALUES(?,?,?,?,1) ON CONFLICT(user_id,mac_address,tool_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=1',(p['user_id'],item['mac_address'],item['service_name'],expires))
     c.execute('INSERT INTO mac_access(user_id,mac_address,expires_at) VALUES(?,?,?) ON CONFLICT(user_id,mac_address) DO UPDATE SET expires_at=CASE WHEN mac_access.expires_at>excluded.expires_at THEN mac_access.expires_at ELSE excluded.expires_at END',(p['user_id'],item['mac_address'],expires))
  if decision=='approved' and p['purpose']=='commercial_order':
   for item in c.execute('SELECT * FROM commercial_order_items WHERE payment_request_id=?',(pid,)).fetchall():
    current=c.execute('SELECT expires_at FROM user_commercial_entitlements WHERE user_id=? AND offer_id=? AND hardware_key=?',(p['user_id'],item['offer_id'],item['hardware_key'])).fetchone()
    period=item['billing_period'];expires=subscription_expiry(current['expires_at'] if current else None,period)
    c.execute('INSERT INTO user_commercial_entitlements(user_id,offer_id,hardware_key,expires_at,enabled,activated_at,updated_at) VALUES(?,?,?,?,1,?,?) ON CONFLICT(user_id,offer_id,hardware_key) DO UPDATE SET expires_at=excluded.expires_at,enabled=1,updated_at=excluded.updated_at',(p['user_id'],item['offer_id'],item['hardware_key'],expires,now(),now()))
    offer=c.execute('SELECT * FROM commercial_offers WHERE id=?',(item['offer_id'],)).fetchone()
    if offer and offer['offer_key']=='game-of-thien':
     c.execute("INSERT INTO account_project_licenses(user_id,service_name,expires_at,enabled,activated_at,updated_at) VALUES(?,'game-of-thien',?,1,?,?) ON CONFLICT(user_id,service_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=1,updated_at=excluded.updated_at",(p['user_id'],expires,now(),now()))
    elif offer and offer['requires_hardware']:
     c.execute('INSERT INTO mac_tool_licenses(user_id,mac_address,tool_name,expires_at,enabled) VALUES(?,?,?,?,1) ON CONFLICT(user_id,mac_address,tool_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=1',(p['user_id'],item['hardware_key'],offer['offer_key'],expires))
  if decision=='approved' and p['purpose']=='service_activation':
   service=p['service_name']; mac=p['mac_address']; days=p['duration_days'] or 365
   current=c.execute('SELECT expires_at FROM mac_tool_licenses WHERE user_id=? AND mac_address=? AND tool_name=?',(p['user_id'],mac,service)).fetchone()
   start=datetime.now(timezone.utc)
   if current:
    try:
     existing=datetime.fromisoformat(current['expires_at'])
     if existing.tzinfo is None: existing=existing.replace(tzinfo=timezone.utc)
     if existing>start:start=existing
    except (TypeError,ValueError):pass
   expires=(start+timedelta(days=days)).isoformat(timespec='seconds')
   c.execute('INSERT OR IGNORE INTO mac_service_profiles(user_id,mac_address,created_at) VALUES(?,?,?)',(p['user_id'],mac,now()))
   c.execute('INSERT INTO mac_tool_licenses(user_id,mac_address,tool_name,expires_at,enabled) VALUES(?,?,?,?,1) ON CONFLICT(user_id,mac_address,tool_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=1',(p['user_id'],mac,service,expires))
   mac_current=c.execute('SELECT expires_at FROM mac_access WHERE user_id=? AND mac_address=?',(p['user_id'],mac)).fetchone()
   mac_expiry=expires
   if mac_current:
    try:
     old=datetime.fromisoformat(mac_current['expires_at'])
     new=datetime.fromisoformat(expires)
     if old>new:mac_expiry=mac_current['expires_at']
    except (TypeError,ValueError):pass
   c.execute('INSERT INTO mac_access(user_id,mac_address,expires_at) VALUES(?,?,?) ON CONFLICT(user_id,mac_address) DO UPDATE SET expires_at=excluded.expires_at',(p['user_id'],mac,mac_expiry))
  detail=f"payment={pid}; purpose={p['purpose']}; amount={p['amount']}; reference={p['reference']}; service={p['service_name']}; mac={p['mac_address']}; decision={decision}"
  c.execute('INSERT INTO admin_logs(admin_user_id,user_id,action,details,created_at) VALUES(?,?,?,?,?)',(current_user()['id'],p['user_id'],'payment_'+decision,detail,now()))
 return redirect('/admin')
@app.post('/admin/settings')
@admin_only
def settings_save():
 check_csrf()
 with db() as c:
  for k in ('bank_name','bank_account','bank_owner','donate_note','qr_url'):c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,request.form.get(k,'')))
 return redirect('/admin')

@app.get('/admin/payments/export.txt')
@admin_only
def payment_log_export():
 with db() as c:
  payments=c.execute("SELECT p.*,u.email,a.name_vi FROM payment_requests p JOIN users u ON u.id=p.user_id LEFT JOIN assets a ON a.id=p.asset_id ORDER BY p.id DESC").fetchall()
  logs=c.execute("SELECT l.*,a.email AS admin_email,u.email AS user_email FROM admin_logs l LEFT JOIN users a ON a.id=l.admin_user_id LEFT JOIN users u ON u.id=l.user_id ORDER BY l.id DESC").fetchall()
 lines=['THIÊN HẠ - THANH TOÁN, KÍCH HOẠT VÀ NHẬT KÝ DUYỆT','Xuất lúc: '+now(),'='*88,'','[GIAO DỊCH]']
 for p in payments:
  subject=(p['service_name']+' @ '+p['mac_address']) if p['purpose']=='service_activation' else (p['name_vi'] or p['purpose'])
  lines.append(f"#{p['id']} | {p['created_at']} | {p['email']} | {subject} | {p['amount']:,} VND | {p['reference']} | {p['status']} | duyệt: {p['reviewed_at'] or '-'}")
 lines.extend(['','[NHẬT KÝ ADMIN]'])
 for row in logs: lines.append(f"#{row['id']} | {row['created_at']} | admin={row['admin_email'] or row['admin_user_id']} | user={row['user_email'] or row['user_id']} | {row['action']} | {row['details']}")
 body='\ufeff'+'\r\n'.join(lines)+'\r\n'
 return Response(body,mimetype='text/plain; charset=utf-8',headers={'Content-Disposition':'attachment; filename=thienha-payment-activation-log.txt'})

@app.get('/projects/xiaozhi-esp32')
def xiaozhi_project():
 edit_mode=bool(is_admin() and request.args.get('edit')=='1')
 with db() as c: row=c.execute("SELECT value FROM settings WHERE key='xiaozhi_page_html'").fetchone()
 if row and row['value']:
  content=row['value'].replace('/static/xiaozhi-copper-wiring.png','/static/xiaozhi-copper-wiring-v7.png')
  return render_template('xiaozhi_custom.html',content_html=content,edit_mode=edit_mode)
 return render_template('xiaozhi_project.html',edit_mode=edit_mode)

@app.post('/admin/xiaozhi-page/save')
@admin_only
def xiaozhi_page_save():
 if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','')):abort(400)
 content=str((request.get_json(silent=True) or {}).get('content_html',''))
 if not content or len(content)>1_500_000:abort(400)
 content=re.sub(r'<script\b[^>]*>[\s\S]*?</script\s*>','',content,flags=re.I)
 content=re.sub(r'\s+on[a-z]+\s*=\s*(["\']).*?\1','',content,flags=re.I|re.S)
 content=re.sub(r'(href|src)\s*=\s*(["\'])\s*javascript:.*?\2',r'\1="#"',content,flags=re.I|re.S)
 with db() as c:
  old=c.execute("SELECT value FROM settings WHERE key='xiaozhi_page_html'").fetchone()
  if old and old['value']:c.execute("INSERT INTO page_revisions(page_slug,content_html,created_by,created_at) VALUES('xiaozhi-esp32',?,?,?)",(old['value'],current_user()['id'],now()))
  c.execute("INSERT INTO settings(key,value) VALUES('xiaozhi_page_html',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(content,))
 return jsonify(ok=True)

@app.post('/admin/xiaozhi-page/reset')
@admin_only
def xiaozhi_page_reset():
 check_csrf()
 with db() as c:
  old=c.execute("SELECT value FROM settings WHERE key='xiaozhi_page_html'").fetchone()
  if old and old['value']:c.execute("INSERT INTO page_revisions(page_slug,content_html,created_by,created_at) VALUES('xiaozhi-esp32',?,?,?)",(old['value'],current_user()['id'],now()))
  c.execute("DELETE FROM settings WHERE key='xiaozhi_page_html'")
 return redirect('/projects/xiaozhi-esp32?edit=1')

@app.post('/activate-game-trial')
def activate_game_trial():
 u=current_user()
 if not u:return redirect(url_for('login',next='/support?service=game-of-thien'))
 check_csrf()
 with db() as c:
  current=c.execute("SELECT expires_at,enabled FROM account_project_licenses WHERE user_id=? AND service_name='game-of-thien'",(u['id'],)).fetchone()
  if current and current['enabled'] and (not current['expires_at'] or datetime.fromisoformat(current['expires_at'])>datetime.now(TZ)):return redirect('/account')
  expires=(datetime.now(TZ)+timedelta(days=7)).isoformat(timespec='seconds')
  c.execute("INSERT INTO account_project_licenses(user_id,service_name,expires_at,enabled,activated_at,updated_at) VALUES(?,'game-of-thien',?,1,?,?) ON CONFLICT(user_id,service_name) DO UPDATE SET expires_at=excluded.expires_at,enabled=1,updated_at=excluded.updated_at",(u['id'],expires,now(),now()))
 return redirect('/account')


with db() as c:
 c.execute("""CREATE TABLE IF NOT EXISTS commercial_offers(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,offer_key TEXT NOT NULL,offer_type TEXT NOT NULL CHECK(offer_type IN ('service','firmware','software','license')),display_name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',requires_hardware INTEGER NOT NULL DEFAULT 0,price_month INTEGER NOT NULL DEFAULT 0,price_year INTEGER NOT NULL DEFAULT 0,price_lifetime INTEGER NOT NULL DEFAULT 0,enabled INTEGER NOT NULL DEFAULT 0,cancelable INTEGER NOT NULL DEFAULT 1,sort_order INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,UNIQUE(project_id,offer_key))""")
 c.execute("""CREATE TABLE IF NOT EXISTS commercial_order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,payment_request_id INTEGER NOT NULL REFERENCES payment_requests(id) ON DELETE CASCADE,offer_id INTEGER NOT NULL REFERENCES commercial_offers(id),billing_period TEXT NOT NULL,hardware_key TEXT NOT NULL DEFAULT '',unit_price INTEGER NOT NULL,duration_days INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL)""")
 c.execute("""CREATE TABLE IF NOT EXISTS user_commercial_entitlements(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,offer_id INTEGER NOT NULL REFERENCES commercial_offers(id) ON DELETE CASCADE,hardware_key TEXT NOT NULL DEFAULT '',expires_at TEXT,enabled INTEGER NOT NULL DEFAULT 1,activated_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,offer_id,hardware_key))""")
 x=c.execute("SELECT id FROM projects WHERE slug='xiaozhi-esp32'").fetchone(); g=c.execute("SELECT id FROM projects WHERE slug='game-of-thien'").fetchone()
 if x:
  for row in c.execute("SELECT * FROM service_catalog WHERE enabled=1"):
   c.execute("INSERT OR IGNORE INTO commercial_offers(project_id,offer_key,offer_type,display_name,description,requires_hardware,price_month,price_year,price_lifetime,enabled,cancelable,sort_order,updated_at) VALUES(?,?, 'service',?,?,1,?,?,?,1,1,?,?)",(x['id'],row['service_name'],row['display_name'],row['description'],row['price_month'],row['price_year'],row['price_lifetime'],row['sort_order'],now()))
 if g:
  c.execute("INSERT OR IGNORE INTO commercial_offers(project_id,offer_key,offer_type,display_name,description,requires_hardware,price_month,price_year,price_lifetime,enabled,cancelable,sort_order,updated_at) VALUES(?,'game-of-thien','license','Game Of Thiên · Quyền truy cập','Mở phiên học có kiểm soát và quản lý thời lượng theo tài khoản.',0,30000,300000,1000000,1,1,10,?)",(g['id'],now()))

# GAME_OF_THIEN_SESSION_START
GAME_OF_THIEN_LIBRARY = {
    'listen-image-en': {'name': 'Nghe tên chọn hình (EN)', 'description': 'Nghe tiếng Anh, chọn đúng hình', 'mark': '🎧', 'ages': '4–10'},
    'listen-image-vi': {'name': 'Nghe tên chọn hình (VI)', 'description': 'Nghe tiếng Việt, chọn đúng hình', 'mark': '🔊', 'ages': '3–9'},
    'puzzle': {'name': 'Ghép hình đúng theo mẫu', 'description': 'Quan sát và ghép hình', 'mark': '🧩', 'ages': '4–10'},
    'sudoku': {'name': 'Sudoku', 'description': 'Tư duy số và logic', 'mark': '123', 'ages': '6–12'},
    'image-answer': {'name': 'Nhìn hình chọn đáp án', 'description': 'Nhận biết và gọi tên', 'mark': '▣', 'ages': '3–10'},
    'count': {'name': 'Học đếm số, đếm hình ảnh', 'description': 'Con số và phép đếm', 'mark': '●●', 'ages': '3–8'},
    'alphabet-en': {'name': 'Học bảng chữ cái tiếng Anh', 'description': 'Chữ và âm tiếng Anh', 'mark': 'ABC', 'ages': '4–9'},
    'alphabet-vi': {'name': 'Học bảng chữ cái tiếng Việt', 'description': 'Chữ và âm tiếng Việt', 'mark': 'ĂÂ', 'ages': '4–9'},
    'memory': {'name': 'Lật cặp hình giống nhau', 'description': 'Quan sát và ghi nhớ', 'mark': '◇◇', 'ages': '4–11'},
    'bomber': {'name': 'Phá bom', 'description': 'Ghi nhớ trình tự', 'mark': '💣', 'ages': '6–12'},
    'hidden-object': {'name': 'Tìm vật mẫu bị giấu', 'description': 'Quan sát và tập trung', 'mark': '⌕', 'ages': '4–12'},
    'tic-tac-toe': {'name': 'Cờ caro (2 người chơi)', 'description': 'Chiến thuật hai người', 'mark': 'XO', 'ages': '5–12'},
    'colors': {'name': 'Học màu sắc', 'description': 'Nhận biết màu sắc', 'mark': '●▲', 'ages': '3–7'},
    'space-shooter': {'name': 'Phi thuyền bắn thiên thạch', 'description': 'Phản xạ và nâng cấp đạn', 'mark': '🚀', 'ages': '6–12'},
    'math-basic': {'name': 'Học phép toán cơ bản', 'description': 'Cộng, trừ và so sánh', 'mark': '+−', 'ages': '5–10'},
    'math-advanced': {'name': 'Học phép toán nâng cao', 'description': 'Nhân, chia và nhiều bước', 'mark': '×÷', 'ages': '7–12'},
    'match-transport': {'name': 'Nối phương tiện với giao thông', 'description': 'Phân loại phương tiện', 'mark': '🚗', 'ages': '4–10'},
    'match-habitat': {'name': 'Nối động vật với môi trường', 'description': 'Động vật và nơi sống', 'mark': '🦁', 'ages': '4–10'},
}

with db() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS game_sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        status TEXT NOT NULL DEFAULT 'ready',
        config_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        started_at TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions_user_created ON game_sessions(user_id, created_at)")

def game_of_thien_access(user):
    state = {'active': False, 'expires_at': None, 'label': None}
    if not user:
        return state
    with db() as c:
        row = c.execute("SELECT expires_at,enabled FROM account_project_licenses WHERE user_id=? AND service_name='game-of-thien'", (user['id'],)).fetchone()
    if not row or not row['enabled']:
        return state
    expires_at = row['expires_at']
    if expires_at:
        try:
            end = datetime.fromisoformat(expires_at)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end <= datetime.now(TZ):
                return state
            state['label'] = 'đến ' + end.astimezone(TZ).strftime('%d/%m/%Y')
        except (TypeError, ValueError):
            return state
    else:
        state['label'] = 'trọn đời'
    state['active'] = True
    state['expires_at'] = expires_at
    return state

@app.get('/projects/game-of-thien')
def game_of_thien_project():
    user = current_user()
    return render_template('game_of_thien.html', game_user=user, game_access=game_of_thien_access(user), game_library=GAME_OF_THIEN_LIBRARY)

@app.post('/projects/game-of-thien/sessions')
def create_game_of_thien_session():
    user = current_user()
    if not user:
        return jsonify(ok=False, message='Vui lòng đăng nhập tài khoản Thiên Hạ trước khi mở phiên'), 401
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(ok=False, message='Thông tin phiên chưa hợp lệ'), 400
    if not session.get('csrf') or not secrets.compare_digest(str(payload.get('csrf', '')), session['csrf']):
        return jsonify(ok=False, message='Phiên đăng nhập đã thay đổi, vui lòng tải lại trang'), 400
    if not game_of_thien_access(user)['active']:
        return jsonify(ok=False, message='Vui lòng kích hoạt Game of Thiên trước khi mở phiên'), 403

    duration = payload.get('duration_minutes')
    if type(duration) is not int or duration not in (10, 20, 30, 40, 50, 60):
        return jsonify(ok=False, message='Thời lượng phiên cần là 10, 20, 30, 40, 50 hoặc 60 phút'), 400
    games = [dict(id=game_id, name=game['name'], ages=game['ages'])
             for game_id, game in GAME_OF_THIEN_LIBRARY.items()]

    token = secrets.token_urlsafe(32)
    created = datetime.now(TZ)
    expires = created + timedelta(minutes=duration)
    config = {'games': games, 'duration_minutes': duration, 'total_duration_minutes': duration, 'version': 2}
    with db() as c:
        c.execute(
            "INSERT INTO game_sessions(token,user_id,status,config_json,created_at,expires_at) VALUES(?,?,?,?,?,?)",
            (token, user['id'], 'ready', json.dumps(config, ensure_ascii=False), created.isoformat(timespec='seconds'), expires.isoformat(timespec='seconds')),
        )
    launch_url = 'https://gameofthien.thienha.io.vn/?session=' + urllib.parse.quote(token, safe='')
    return jsonify(ok=True, launch_url=launch_url, expires_at=expires.isoformat(timespec='seconds'))

@app.get('/api/game-of-thien/sessions/<token>')
def get_game_of_thien_session(token):
    if len(token) < 32 or len(token) > 96:
        return jsonify(ok=False, message='Phiên không tồn tại'), 404
    with db() as c:
        row = c.execute("SELECT status,config_json,created_at,expires_at,started_at FROM game_sessions WHERE token=?", (token,)).fetchone()
    if not row:
        return jsonify(ok=False, message='Phiên không tồn tại'), 404
    try:
        expires = datetime.fromisoformat(row['expires_at'])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return jsonify(ok=False, message='Phiên không hợp lệ'), 410
    if expires <= datetime.now(TZ) or row['status'] not in ('ready', 'started'):
        return jsonify(ok=False, message='Phiên đã kết thúc'), 410
    response = jsonify(
        ok=True,
        status=row['status'],
        config=json.loads(row['config_json']),
        created_at=row['created_at'],
        expires_at=row['expires_at'],
        started_at=row['started_at'],
        server_now=datetime.now(TZ).isoformat(timespec='milliseconds'),
    )
    response.headers['Access-Control-Allow-Origin'] = 'https://gameofthien.thienha.io.vn'
    response.headers['Vary'] = 'Origin'
    response.headers['Cache-Control'] = 'no-store'
    return response
# GAME_OF_THIEN_SESSION_END
@app.get('/projects/xiaozhi-esp32/install')
def xiaozhi_install():
 if not current_user(): return redirect(url_for('login',next=request.path))
 return render_template('xiaozhi_install.html')
@app.get('/download/xiaozhi-release')
def xiaozhi_release_download():
 u=current_user()
 if not u: return redirect(url_for('login',next=request.path))
 with db() as c: c.execute("INSERT INTO activity(user_id,item_type,item_id,item_name,created_at) VALUES(?,?,?,?,?)",(u['id'],'firmware',0,'XiaoZhi Copper Robot 2.4.0',now()))
 return send_file(FILES/'xiaozhi-copper-robot-2.4.0-complete.zip',as_attachment=True,download_name='xiaozhi-copper-robot-2.4.0-complete.zip')
@app.get('/healthz')
def health():
 try:
  with db() as c: c.execute('SELECT 1 FROM projects LIMIT 1').fetchall()
 except sqlite3.Error:
  return jsonify(ok=False), 503
 return jsonify(ok=True, service='thienha-portal', revision=os.environ.get('APP_REVISION', 'development'))
from xiaozhi_tools import register_xiaozhi_tools
register_xiaozhi_tools(app)
if __name__=='__main__': app.run('127.0.0.1',5050,threaded=True)
