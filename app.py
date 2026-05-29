from flask import Flask, render_template, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from init_db import User, CurrentDorm, WishList

app = Flask(__name__)

engine = create_engine("sqlite:///dorm_exchange.db")
Session = sessionmaker(bind=engine)

# 男生女生資格防呆邏輯
# 男生女生與學院資格防呆邏輯 (加入南大校區藝術學院規則)
def check_dorm_eligibility(user_gender, user_degree, is_college_member, is_art_student, target_dorm, target_room_type):
    # 定義南大校區的宿舍清單
    nanda_dorms = ['鳴風樓', '樂善樓', '迎曦軒', '擁月齋', '樹德樓']

    # 1. 藝術學院專屬限制：如果是藝術學院，只能選南大校區的宿舍
    if is_art_student and (target_dorm not in nanda_dorms):
        return False, f"失敗：藝術學院學生依規定「僅限」選擇南大校區宿舍（如：鳴風樓、樂善樓、迎曦軒、擁月齋、樹德樓）。"

    # 2. 共通限制：仁齋、實齋限住宿書院 (不分男女)
    if target_dorm in ['仁齋', '實齋'] and not is_college_member:
        return False, f"失敗：{target_dorm}僅限「住宿書院」成員選擇。"

    # 3. 男生專屬規則與限制
    if user_gender == 'M':
        # 校本部女生宿舍 + 南大女生宿舍
        female_only_dorms = ['靜齋', '慧齋', '雅齋', '文齋', '鳴風樓', '迎曦軒', '擁月齋']                                                                                                                      
        if target_dorm in female_only_dorms:
            # 特例排除：擁月齋跟樂善樓有研究所/大學部混合，但鳴風、迎曦純女宿。樹德純男宿。
            # 根據表格：樹德樓是男生宿舍。
            return False, f"失敗：{target_dorm}為女生宿舍或無男生床位，男生無法選擇。"
        if target_dorm in ['學齋', '儒齋'] and user_degree != 'grad':
            return False, f"失敗：男生的{target_dorm}僅限「研究所」學生選擇。"

    # 4. 女生專屬規則與限制
    elif user_gender == 'F':
        # 校本部男生宿舍 + 南大樹德樓(純男宿)
        male_only_dorms = ['義齋', '禮齋', '智齋', '誠齋', '明齋', '樹德樓']
        if target_dorm in male_only_dorms:
            return False, f"失敗：{target_dorm}為男生宿舍，女生無法選擇。"
        if target_dorm == '學齋' and user_degree != 'grad':
            return False, "失敗：女生的學齋僅限「研究所」學生選擇。"
        if target_dorm == '儒齋' and target_room_type == '單人房' and user_degree != 'grad':
            return False, "失敗：女生的儒齋單人房僅限「研究所」學生選擇。"

    return True, "驗證成功：符合該宿舍入住資格。"

# 雙向配對演算法
def run_two_way_match():
    session = Session()
    print("\n=== 開始執行雙向配對演算法 ===")
    active_wishes = session.query(WishList).filter(WishList.status == "matching").all()
    
    for i in range(len(active_wishes)):
        for j in range(i + 1, len(active_wishes)):
            wish_a = active_wishes[i]
            wish_b = active_wishes[j]
            user_a = wish_a.user
            user_b = wish_b.user
            current_a = user_a.current_dorm
            current_b = user_b.current_dorm
            
            match_1 = (wish_a.preferred_dorm == current_b.dorm_name and wish_a.preferred_room_type == current_b.room_type)
            match_2 = (wish_b.preferred_dorm == current_a.dorm_name and wish_b.preferred_room_type == current_a.room_type)
            
            if match_1 and match_2:
                print(f"🎉 找到完美配對！")
                # 將狀態改成對方的使用者ID，以便互相查詢聯絡方式
                wish_a.status = f"matched_with_{user_b.id}"
                wish_b.status = f"matched_with_{user_a.id}"
                session.commit()
                session.close()
                return
    session.close()

@app.route("/")
def home():
    return render_template("index.html")
@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form.get("student_id")
    name = request.form.get("name")
    gender = request.form.get("gender")
    degree = request.form.get("degree")
    is_college = request.form.get("is_college") == "True"
    is_art_student = request.form.get("is_art_student") == "True"
    line_id = request.form.get("line_id")
    current_dorm_name = request.form.get("current_dorm")
    current_type = request.form.get("current_type")
    
    wishes_to_check = [
        {"dorm": request.form.get("pref_dorm_1"), "type": request.form.get("pref_type_1"), "order": 1},
        {"dorm": request.form.get("pref_dorm_2"), "type": request.form.get("pref_type_2"), "order": 2},
        {"dorm": request.form.get("pref_dorm_3"), "type": request.form.get("pref_type_3"), "order": 3}
    ]

    for wish in wishes_to_check:
            if wish["dorm"] and wish["type"]:
                
                # 【關鍵這幾行】：確保這段呼叫防呆的程式碼還在，而且左邊縮排正確！
                is_valid, message = check_dorm_eligibility(
                    user_gender=gender, 
                    user_degree=degree, 
                    is_college_member=is_college, 
                    is_art_student=is_art_student, 
                    target_dorm=wish["dorm"], 
                    target_room_type=wish["type"]
                )
                
                # 下面接原本擋下亂碼的防呆退件
                if not is_valid:
                    return f"""
                    <meta charset="UTF-8">
                    <h2>❌ 申請失敗</h2>
                    <p>您的第 {wish['order']} 志願不符資格：<span style="color:red; font-weight:bold;">{message}</span></p>
                    <br><a href='/'>返回重新填寫</a>
                    """
    session = Session()
    try:
        existing_user = session.query(User).filter(User.student_id == student_id).first()
        if existing_user:
            session.query(WishList).filter(WishList.user_id == existing_user.id).delete()
            session.query(CurrentDorm).filter(CurrentDorm.user_id == existing_user.id).delete()
            session.delete(existing_user)
            session.commit() 

        new_user = User(student_id=student_id, name=name, gender=gender, degree=degree, is_college_member=is_college, line_id=line_id, email=f"{student_id}@email.com")
        session.add(new_user)
        session.commit() 
        
        new_current = CurrentDorm(user_id=new_user.id, dorm_name=current_dorm_name, room_type=current_type, room_number="101", bed_number="A")
        session.add(new_current)
        
        for wish in wishes_to_check:
            if wish["dorm"] and wish["type"]:
                new_wish = WishList(user_id=new_user.id, preferred_dorm=wish["dorm"], preferred_room_type=wish["type"], preference_order=wish["order"], status="matching")
                session.add(new_wish)
        session.commit()
        return "<h2>🎉 填寫/更新成功！</h2><p>系統已成功儲存您的多項志願，並重新進行最佳推薦計算！</p><a href='/'>返回首頁</a>"
    except Exception as e:
        session.rollback()
        return f"""
        <meta charset="UTF-8">
        <h2>❌ 發生錯誤</h2>
        <p>儲存資料時發生問題：({e})</p>
        <br><a href='/'>返回</a>
        """
    finally:
        session.close()

# ==========================================
# 功能二：智慧推薦清單（查詢按鈕專用，就是你截圖上的這段）
# ==========================================

@app.route("/check_result", methods=["POST"])
def check_result():
    search_id = request.form.get("search_student_id")
    session = Session()
    
    # 1. 找到查詢的這位同學 (我們稱他為「主學生」)
    me = session.query(User).filter(User.student_id == search_id).first()
    if not me:
        session.close()
        return "<h2>🔍 查詢結果</h2><p>找不到此學號，請先填寫表單。</p><a href='/'>返回</a>"
    
    # 2. 撈出這位同學「目前擁有的宿舍」與「所有志願」
    my_dorm = me.current_dorm
    my_wishes = session.query(WishList).filter(WishList.user_id == me.id).order_by(WishList.preference_order).all()
    
    # 3. 撈出資料庫裡「其他所有人」，準備兩兩比對計分
    all_other_users = session.query(User).filter(User.id != me.id).all()
    
    recommend_list = [] # 用來放所有可能的候選人與分數

    for other in all_other_users:
        other_dorm = other.current_dorm
        other_wishes = session.query(WishList).filter(WishList.user_id == other.id).order_by(WishList.preference_order).all()
        
        # 如果對方連目前宿舍都沒填，就跳過
        if not other_dorm:
            continue
            
        score = 0
        reason = []
        
        # 【計分邏輯 A】：對方目前的宿舍，符合我的第幾志願？
        my_match_order = None
        for w in my_wishes:
            if other_dorm.dorm_name == w.preferred_dorm and other_dorm.room_type == w.preferred_room_type:
                my_match_order = w.preference_order
                break
                
        # 【計分邏輯 B】：我目前的宿舍，符合對方的第幾志願？
        other_match_order = None
        for w in other_wishes:
            if my_dorm.dorm_name == w.preferred_dorm and my_dorm.room_type == w.preferred_room_type:
                other_match_order = w.preference_order
                break

        # 【計算總分】
        # 狀況一：雙向完美互補（你想去他家，他想去你家）
        if my_match_order and other_match_order:
            if my_match_order == 1 and other_match_order == 1:
                score = 100
                reason.append("🔥 雙向第一志願完美互補！")
            else:
                score = 80 - (my_match_order + other_match_order) * 5
                reason.append(f"✨ 雙向契合！（符合您的第 {my_match_order} 志願，對方的第 {other_match_order} 志願）")
                
        # 狀況二：單向符合（他想來你家，但他的宿舍只是你沒填的特殊齋，或者反過來）
        elif my_match_order and not other_match_order:
            score = 40 - my_match_order * 5
            reason.append(f"📐 單向符合（該宿舍符合您的第 {my_match_order} 志願，但您目前的床位非對方首選）")
            
        elif other_match_order and not my_match_order:
            score = 30 - other_match_order * 5
            reason.append(f"📐 單向潛在機會（對方非常想換您的床位，但他的床位非您的預填志願）")

        # 只要分數大於 0，就代表有機會換，放進推薦清單！
        if score > 0:
            recommend_list.append({
                "name": other.name,
                "line_id": other.line_id,
                "dorm_info": f"{other_dorm.dorm_name} ({other_dorm.room_type})",
                "score": score,
                "reason": ", ".join(reason)
            })

    # 4. 【核心排序】：把清單依照分數「從高到低」重新排列！
    recommend_list.sort(key=lambda x: x["score"], reverse=True)

    # 5. 把結果組裝成 HTML 顯示在網頁上
    if not recommend_list:
        session.close()
        return "<h2>🔍 智慧媒合結果</h2><p>⏳ 媒合中！目前資料庫中尚無與您條件交集的同學，請邀請更多同學填寫！</p><a href='/'>返回首頁</a>"

    html_output = f"<h2>🔍 為您找到的推薦交換清單 (依契合度排序)</h2>"
    html_output += f"<p>系統已為學號 <b>{search_id}</b> 現場計算最佳配對，以下對象依推薦指數由高到低排列：</p>"
    
    for idx, item in enumerate(recommend_list):
        html_output += f"""
        <div style="background: white; padding: 20px; margin-bottom: 15px; border-radius: 6px; border-left: 6px solid #2ecc71; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h3 style="margin-top:0; color:#2c3e50;">🎯 推薦順位 {idx+1} （推薦指數：{item['score']} 分）</h3>
            <p><b>🔍 媒合原因：</b> <span style="color:#e67e22;">{item['reason']}</span></p>
            <ul>
                <li><b>同學稱呼：</b> {item['name'][0]}同學 (隱私保護)</li>
                <li><b>他目前擁有的床位：</b> <span style="color:green; font-weight:bold;">{item['dorm_info']}</span></li>
                <li><b>聯絡他的 LINE ID：</b> <span style="color:blue; font-size:18px; font-family:monospace;">{item['line_id']}</span></li>
            </ul>
        </div>
        """
    
    html_output += "<br><a href='/'>返回首頁</a>"
    session.close()
    return html_output

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)