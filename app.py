from flask import Flask, render_template, request, session, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from init_db import User, CurrentDorm, WishList

# ==========================================
# 1. 基礎核心設定
# ==========================================
app = Flask(__name__)
app.secret_key = 'super_secret_key_dorm_system_2026'
import os
# 🎯 兩邊同步鎖死絕對路徑
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENGINE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'dorm_exchange.db')}"
engine = create_engine(ENGINE_URL)
Session = sessionmaker(bind=engine)

# ==========================================
# 2. 核心路由：首頁面版 (💡 已加上全面防爆機制)
# ==========================================
@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html', user_wish=None)
        
    db_session = Session()
    user_me = db_session.query(User).filter_by(student_id=session['user_id']).first()
    
    user_wish = None
    matched_dorm_info = ""
    new_dorm_info = ""
    
    if user_me and user_me.wishes:
        user_wish = user_me.wishes[-1] 
        
        # 🌟 狀態一：只要有指派對象 (status 為 proposed 或 my_approved)，都需要安全撈出對方宿舍，不能讓首頁崩潰
        if user_wish.status in ['proposed', 'my_approved'] and user_wish.matched_wish_id:
            opp_wish = db_session.query(WishList).get(user_wish.matched_wish_id)
            if opp_wish and opp_wish.user:
                opp_dorm = opp_wish.user.current_dorm
                if opp_dorm:
                    matched_dorm_info = f"{opp_dorm.dorm_name} - {opp_dorm.room_type} (房號隱蔽)"
                else:
                    matched_dorm_info = "未分配宿舍 - 四人房"
                
        # 🌟 狀態二：雙方同意，交換大成功 (approved)
        elif user_wish.status == 'approved':
            if user_me.current_dorm:
                new_dorm_info = f"{user_me.current_dorm.dorm_name} ({user_me.current_dorm.room_type})"
            else:
                new_dorm_info = "分配成功 (暫無齋舍資料)"

    db_session.close()
    return render_template('index.html', 
                           user_wish=user_wish, 
                           matched_dorm_info=matched_dorm_info,
                           new_dorm_info=new_dorm_info)

# ==========================================
# 3. 核心路由：註冊與登入登出
# ==========================================
@app.route('/register', methods=['POST'])
def register():
    student_id = request.form.get('student_id', '').strip()
    name = request.form.get('name', '').strip()
    gender = request.form.get('gender', '').strip()
    degree = request.form.get('degree', '').strip()
    line_id = request.form.get('line_id', '').strip()
    password = request.form.get('password', '').strip()
    is_college = request.form.get('is_college') == 'True'
    email = f"{student_id}@oz.nthu.edu.tw"

    db_session = Session()
    try:
        existing_user = db_session.query(User).filter_by(student_id=student_id).first()
        if existing_user:
            return "<meta charset='UTF-8'><h2>❌ 註冊失敗</h2><p>該學號已經註冊過帳號！</p><br><a href='/'>返回</a>"
        
        new_user = User(
            student_id=student_id, name=name, gender=gender, degree=degree,
            is_college_member=is_college, line_id=line_id, email=email, points=100
        )
        new_user.set_password(password)

        db_session.add(new_user)
        db_session.commit()
        return "<meta charset='UTF-8'><h2>🎉 註冊成功！</h2><p>請返回首頁登入。</p><br><a href='/'>前往登入</a>"
    except Exception as e:
        db_session.rollback()
        return f"<meta charset='UTF-8'><h2>❌ 註冊錯誤</h2><p>{e}</p>"
    finally:
        db_session.close()

@app.route('/login', methods=['POST'])
def login():
    student_id = request.form.get('student_id', '').strip()
    password = request.form.get('password', '').strip()
    
    db_session = Session()
    user = db_session.query(User).filter(User.student_id == student_id).first()
    db_session.close()
    
    if user and user.check_password(password):
        session['user_id'] = user.student_id
        session['user_name'] = user.name
        return redirect('/') 
    else:
        return "<meta charset='UTF-8'><h2>❌ 登入失敗</h2><p>學號或密碼錯誤！</p><br><a href='/'>返回</a>"

@app.route('/logout')
def logout():
    session.clear() 
    return redirect('/')

# ==========================================
# 4. 後台業務邏輯：齋舍交換資格防呆驗證
# ==========================================
def check_dorm_eligibility(user_gender, user_degree, is_college_member, is_art_student, target_dorm, target_room_type):
    nanda_dorms = ['鳴風樓', '樂善樓', '迎曦軒', '擁月齋', '樹德樓']

    if is_art_student and (target_dorm not in nanda_dorms):
        return False, f"失敗：藝術學院學生依規定僅限選擇南大校區宿舍。"

    if target_dorm in ['仁齋', '實齋'] and not is_college_member:
        return False, f"失敗：{target_dorm}僅限「住宿書院」成員選擇。"

    if user_gender == 'M':
        female_only_dorms = ['靜齋', '慧齋', '雅齋', '信齋A', '信齋B', '學齋', '鳴風樓', '迎曦軒', '擁月齋']                                                                                                                                                                                                         
        if target_dorm in female_only_dorms:
            return False, f"失敗：{target_dorm}為純女生宿舍，男生無法選擇。"
        
        if target_dorm in ['明齋', '平齋'] and user_degree != 'grad':
            return False, f"失敗：{target_dorm}僅限「研究所」男生選填。"
        
        undergrad_only_male = ['華齋', '碩齋', '誠齋', '新齋', '信齋C棟', '義齋', '禮齋']
        if target_dorm in undergrad_only_male and user_degree != 'undergrad':
            return False, f"失敗：{target_dorm}僅限「大學部」男生選填。"

    elif user_gender == 'F':
        male_only_dorms = ['智齋', '誠齋', '明齋', '平齋', '華齋', '碩齋', '信齋C棟', '樹德樓', '義齋', '禮齋']
        if target_dorm in male_only_dorms:
            return False, f"失敗：{target_dorm}為男生宿舍，女生無法選擇。"

        if target_dorm == '學齋' and user_degree != 'grad':
            return False, "失敗：學齋僅限「研究所」女生選填。"
            
        if target_dorm == '儒齋' and target_room_type == '單人房' and user_degree != 'grad':
            return False, "失敗：儒齋的單人房僅限「研究所」女生選填。"

        undergrad_only_female = ['信齋A', '信齋B', '靜齋', '慧齋', '雅齋']
        if target_dorm in undergrad_only_female and user_degree != 'undergrad':
            return False, f"失敗：{target_dorm}僅限「大學部」女生選填。"

    return True, "驗證成功"

# ==========================================
# 5. 後台業務邏輯：中央雙盲配對演算法
# ==========================================
def run_two_way_match():
    session_db = Session()
    print("\n=== 🔮 啟動：中央雙盲匿名加權媒合機制 🔮 ===")
    
    active_wishes = session_db.query(WishList).filter(WishList.status == "matching").all()
    
    for wish in active_wishes:
        user = wish.user
        current = user.current_dorm
        if not current: continue
        
        score = wish.allocated_points
        if wish.preference_order == 1: score += 30
        
        nanda_dorms = ['鳴風樓', '樂善樓', '迎曦軒', '擁月齋', '樹德樓']
        if user.is_art_student and (current.dorm_name not in nanda_dorms) and (wish.preferred_dorm in nanda_dorms):
            score += 50 
        if (not user.is_art_student) and (current.dorm_name in nanda_dorms) and (wish.preferred_dorm not in nanda_dorms):
            score += 50 
            
        wish.weight_score = score
    
    session_db.commit() 

    sorted_wishes = session_db.query(WishList).filter(WishList.status == "matching").order_by(WishList.weight_score.desc()).all()
    matched_count = 0
    
    for i in range(len(sorted_wishes)):
        wish_a = sorted_wishes[i]
        if wish_a.status != "matching": continue 
        user_a = wish_a.user
        current_a = user_a.current_dorm
        if not current_a: continue
        
        for j in range(len(sorted_wishes)):
            wish_b = sorted_wishes[j]
            if wish_b.status != "matching" or wish_a.id == wish_b.id: continue
            
            user_b = wish_b.user
            current_b = user_b.current_dorm
            if not current_b: continue
            
            match_1 = (current_b.dorm_name == wish_a.preferred_dorm and current_b.room_type == wish_a.preferred_room_type)
            match_2 = (current_a.dorm_name == wish_b.preferred_dorm and current_a.room_type == wish_b.preferred_room_type)
            
            if match_1 and match_2:
                wish_a.status = "proposed"
                wish_b.status = "proposed"
                wish_a.matched_wish_id = wish_b.id
                wish_b.matched_wish_id = wish_a.id
                
                print(f"🎯 系統成功匿名撮合！願望ID {wish_a.id} ⚖️ 願望ID {wish_b.id}")
                matched_count += 1
                break 
                
    session_db.commit()
    session_db.close()
    print(f"=== 🔮 媒合結束，本次成功撮合 {matched_count} 組對象 ===\n")

# ==========================================
# 6. 核心路由：提交志願表單
# ==========================================
@app.route("/submit", methods=["POST"])
def submit_wishes():
    if 'user_id' not in session:
        return "<meta charset='UTF-8'><h2>🔒 請先登入</h2>"
    
    student_id = request.form.get("student_id", "").strip()
    name = request.form.get("name", "").strip()
    gender = request.form.get("gender", "").strip()
    degree = request.form.get("degree", "").strip()
    is_college = request.form.get("is_college") == "True"
    is_art_student = request.form.get("is_art_student") == "True"
    line_id = request.form.get("line_id", "").strip()
    current_dorm_name = request.form.get("current_dorm")
    current_type = request.form.get("current_type")
    allocated_points = int(request.form.get("allocated_points", 50))
    
    if session['user_id'] != student_id:
        return "<meta charset='UTF-8'><h2>❌ 權限錯誤</h2>"

    wishes_to_check = [
        {"dorm": request.form.get("pref_dorm_1"), "type": request.form.get("pref_type_1"), "order": 1}
    ]

    for wish in wishes_to_check:
        if wish["dorm"] and wish["type"]:
            is_valid, message = check_dorm_eligibility(
                gender, degree, is_college, is_art_student, wish["dorm"], wish["type"]
            )
            if not is_valid:
                return f'<meta charset="UTF-8"><h2>❌ 資格不符</h2><p>{message}</p><a href="/">返回</a>'
                
    session_db = Session()
    try:
        existing_user = session_db.query(User).filter(User.student_id == student_id).first()
        if not existing_user:
            return "<meta charset='UTF-8'><h2>❌ 錯誤</h2><p>找不到該使用者帳號，請先註冊！</p>"
        
        existing_user.name = name
        existing_user.gender = gender
        existing_user.degree = degree
        existing_user.is_college_member = is_college
        existing_user.is_art_student = is_art_student
        existing_user.line_id = line_id
        
        session_db.query(WishList).filter(WishList.user_id == existing_user.id).delete()
        session_db.query(CurrentDorm).filter(CurrentDorm.user_id == existing_user.id).delete()
        session_db.commit()
        
        new_current = CurrentDorm(user_id=existing_user.id, dorm_name=current_dorm_name, room_type=current_type, room_number="101", bed_number="A")
        session_db.add(new_current)
        
        for wish in wishes_to_check:
            if wish["dorm"] and wish["type"]:
                new_wish = WishList(
                    user_id=existing_user.id, preferred_dorm=wish["dorm"], preferred_room_type=wish["type"], 
                    preference_order=wish["order"], allocated_points=allocated_points, status="matching"
                )
                session_db.add(new_wish)
                
        session_db.commit()
        run_two_way_match()
        return "<meta charset='UTF-8'><h2>🎉 成功鎖定並進入中央池！</h2><p>系統已為您重啟媒合輪詢。</p><a href='/'>返回首頁</a>"
    except Exception as e:
        session_db.rollback()
        return f"儲存錯誤：{e}"
    finally:
        session_db.close()

# ==========================================
# 7. 核心路由：雙盲互動確認接收區 (💡 已完美解決跳轉 NoneType 漏洞)
# ==========================================
@app.route('/respond_match', methods=['POST'])
def respond_match():
    if 'user_id' not in session:
        return redirect('/')
        
    wish_id = request.form.get('wish_id')
    choice = request.form.get('choice') 
    
    db_session = Session()
    try:
        my_wish = db_session.query(WishList).get(wish_id)
        if not my_wish or not my_wish.matched_wish_id:
            return "<meta charset='UTF-8'><h2>❌ 操作失敗</h2>"
            
        opp_wish = db_session.query(WishList).get(my_wish.matched_wish_id)
        
        if choice == 'reject':
            my_wish.status = 'matching'
            my_wish.matched_wish_id = None
            if opp_wish:
                opp_wish.status = 'matching'
                opp_wish.matched_wish_id = None
            db_session.commit()
            db_session.close()
            run_two_way_match() 
            return "<meta charset='UTF-8'><h2>↩️ 已退回中央池</h2><p>您已婉拒此床位，重新排隊中。</p><a href='/'>首頁</a>"
            
        elif choice == 'approve':
            if opp_wish.status == 'proposed':
                my_wish.status = 'my_approved'
                db_session.commit()
                db_session.close()
                return "<meta charset='UTF-8'><h2>⏳ 靜候佳音</h2><p>您已同意！正等待對方按下確認，完成雙盲交換。</p><a href='/'>首頁</a>"
                
            elif opp_wish.status == 'my_approved':
                my_wish.status = 'approved'
                opp_wish.status = 'approved'
                
                user_a = my_wish.user
                user_b = opp_wish.user
                
                id_a = user_a.id
                id_b = user_b.id
                
                dorm_rec_a = db_session.query(CurrentDorm).filter(CurrentDorm.user_id == id_a).first()
                dorm_rec_b = db_session.query(CurrentDorm).filter(CurrentDorm.user_id == id_b).first()
                
                if not dorm_rec_a:
                    dorm_rec_a = CurrentDorm(user_id=id_a, dorm_name="靜齋", room_type="四人房", room_number="101", bed_number="A")
                    db_session.add(dorm_rec_a)
                    db_session.commit()
                if not dorm_rec_b:
                    dorm_rec_b = CurrentDorm(user_id=id_b, dorm_name="鳴風樓", room_type="四人房", room_number="102", bed_number="B")
                    db_session.add(dorm_rec_b)
                    db_session.commit()
                
                # 🔀 物理數字強力對調
                dorm_rec_a.user_id = -1
                db_session.commit() # 🚨 先存檔，這時候 id_a 自由了！
                
                # 接著把 B 的擁有者改成 A
                dorm_rec_b.user_id = id_a
                db_session.commit() # 🚨 再存檔，這時候 id_b 自由了！
                
                # 最後把原本改成 -1 的 A 宿舍，正式指派給 B
                dorm_rec_a.user_id = id_b
                db_session.commit() # 🚨 大功告成！
                
                db_session.commit()
                print(f"🔥 [安全連動] 學號 {user_a.student_id} 與 學號 {user_b.student_id} 床位完美對調！")
                db_session.close()
                return redirect('/')
                
    except Exception as e:
        db_session.rollback()
        db_session.close()
        return f"發生錯誤：{e}"
    finally:
        if db_session:
            db_session.close()

# ==========================================
# 8. 核心路由：撤銷申請退出中央池
# ==========================================
@app.route('/cancel_wish', methods=['POST'])
def cancel_wish():
    if 'user_id' not in session:
        return redirect('/')
        
    wish_id = request.form.get('wish_id')
    db_session = Session()
    try:
        my_wish = db_session.query(WishList).get(wish_id)
        if my_wish and my_wish.status == 'matching':
            user_id = my_wish.user_id
            db_session.query(WishList).filter(WishList.user_id == user_id).delete()
            db_session.query(CurrentDorm).filter(CurrentDorm.user_id == user_id).delete()
            db_session.commit()
            print(f"🛑 學號 {session['user_id']} 已成功撤銷申請，退出中央交換池。")
            return "<meta charset='UTF-8'><h2>✅ 撤銷成功</h2><p>您已安全退出中央交換池，目前的床位已解鎖。</p><a href='/'>返回首頁</a>"
        else:
            return "<meta charset='UTF-8'><h2>❌ 撤銷失敗</h2><p>此申請已被指派對象或已完成配對，無法直接撤銷！</p><a href='/'>返回</a>"
    except Exception as e:
        db_session.rollback()
        return f"撤銷錯誤：{e}"
    finally:
        db_session.close()

if __name__ == "__main__":
    # 🚨 ====== 【黑科技：啟動時強制雲端物理點火生表格】 ======
    try:
        from init_db import Base, engine, User
        print("🔮 偵測到雲端啟動，正在強制初始化 SQL 表格與預設測試資料...")
        
        # 1. 強制在資料庫建立所有缺失的表格 (users, current_dorms, wish_lists)
        Base.metadata.create_all(engine)
        
        # 2. 順便自動塞入我們需要的測試帳號，這樣你就連現場註冊都不用了！
        from sqlalchemy.orm import sessionmaker
        TestSession = sessionmaker(bind=engine)
        ts = TestSession()
        
        # 檢查 11 號大苦主是否存在，沒有就自動建立
        user_11 = ts.query(User).filter_by(student_id="113032011").first()
        if not user_11:
            u11 = User(student_id="113032011", name="理學院苦主A", gender="F", degree="undergrad", is_college_member=False, is_art_student=False, line_id="line_a", email="11@oz.nthu.edu.tw")
            u11.set_password("123456")
            ts.add(u11)
            
        # 檢查 12 號本地人是否存在，沒有就自動建立
        user_12 = ts.query(User).filter_by(student_id="113032012").first()
        if not user_12:
            u12 = User(student_id="113032012", name="教育院本地B", gender="F", degree="undergrad", is_college_member=False, is_art_student=False, line_id="line_b", email="12@oz.nthu.edu.tw")
            u12.set_password("123456")
            ts.add(u12)
            
        ts.commit()
        ts.close()
        print("🎉 雲端資料庫地基與預設帳號 (113032011 / 113032012) 完美初始化成功！")
    except Exception as db_err:
        print(f"❌ 啟動初始化發生非致命錯誤（可能表格已存在）: {db_err}")
    # =========================================================

    # 保持 port=5001 與你們的設定完全相容
    app.run(debug=True, host="0.0.0.0", port=5001)