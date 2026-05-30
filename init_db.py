from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# 資料庫基礎連線設定
# ==========================================
ENGINE_URL = "sqlite:///dorm_exchange.db"
engine = create_engine(ENGINE_URL, echo=True)
Session = sessionmaker(bind=engine)

Base = declarative_base()

# ==========================================
# 表格一：User (使用者/學生帳號)
# ==========================================
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    gender = Column(String(10))
    password_hash = Column(String(128), nullable=False)
    degree = Column(String(20), nullable=False)          
    is_college_member = Column(Boolean, default=False)   
    is_art_student = Column(Boolean, default=False)      # 🌟 新增：是否為藝術學院
    line_id = Column(String(50), nullable=False)         
    email = Column(String(100), nullable=False)          
    points = Column(Integer, default=100)                # 🌟 新增：基礎權重點數 100 點
    created_at = Column(DateTime, default=datetime.utcnow)

    current_dorm = relationship("CurrentDorm", uselist=False, back_populates="user")
    wishes = relationship("WishList", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ==========================================
# 表格二：CurrentDorm (目前擁有的床位)
# ==========================================
class CurrentDorm(Base):
    __tablename__ = 'current_dorms'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    dorm_name = Column(String(20), nullable=False)  # 齋別
    room_type = Column(String(20), nullable=False)  # 房型
    room_number = Column(String(10), nullable=False)# 房號
    bed_number = Column(String(10), nullable=False) # 床位

    user = relationship("User", back_populates="current_dorm")


# ==========================================
# 表格三：WishList (期望交換的願望清單)
# ==========================================
class WishList(Base):
    __tablename__ = 'wish_lists'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    preferred_dorm = Column(String(20), nullable=False)  
    preferred_room_type = Column(String(20), nullable=False)  
    preference_order = Column(Integer, nullable=False)   
    allocated_points = Column(Integer, default=0)        # 🌟 新增：同學為此志願投擲的點數
    weight_score = Column(Integer, default=0)            # 🌟 新增：後端計算出的「綜合急迫加權總分」
    
    # 🌟 狀態定義改成： 'matching' (媒合中), 'proposed' (系統指派成功，等待雙方同意), 'approved' (雙方同意，更換成功)
    status = Column(String(20), default="matching")      
    matched_wish_id = Column(Integer, nullable=True)     # 🌟 新增：鎖定對方的志願序 ID (但全程不透露個資)

    user = relationship("User", back_populates="wishes")


# ==========================================
# 執行建立所有表格與初始資料的主程式
# ==========================================
if __name__ == "__main__":
    print("正在初始化資料庫與建立表格...")
    # 確保每次執行都是乾淨的全新表格
    Base.metadata.create_all(engine)
    print("資料庫基本表格建立成功！")

    # 開啟資料庫寫入對話
    session = Session()

    print("正在建立測試學生帳號...")
    # 建立你的學生資料（🔥 這裡幫你把必填的 line_id 和 email 通通補齊了！）
    user_me = User(
        student_id="113032005",  
        name="你的名字",
        gender="M", 
        degree="undergrad",
        is_college_member=False,
        line_id="my_line_id_888",              # 👈 補上必填欄位
        email="113032005@oz.nthu.edu.tw"       # 👈 補上必填欄位
    )

    # 設定你的專屬密碼
    user_me.set_password("123456")  

    # 存進資料庫
    session.add(user_me)
    session.commit()
    session.close()
    
    print("🎉 資料庫完全初始化成功！")
    print("🎓 測試帳號學號：113032005")
    print("🔒 測試帳號密碼：123456")