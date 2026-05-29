from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# 1. 建立資料庫引擎（會自動在當前目錄生成 dorm_exchange.db 檔案）
ENGINE_URL = "sqlite:///dorm_exchange.db"
engine = create_engine(ENGINE_URL, echo=True)

Base = declarative_base()

# ==========================================
# 表格一：User (使用者/學生帳號)
# ==========================================
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, nullable=False)  # 學號
    name = Column(String(50), nullable=False)                     # 姓名
    gender = Column(String(10), nullable=False)                   # 性別：'F' (女), 'M' (男)
    degree = Column(String(20), nullable=False)                   # 學制：'undergrad' (大學部), 'grad' (研究所)
    is_college_member = Column(Boolean, default=False)            # 是否為住宿書院成員
    line_id = Column(String(50), nullable=False)                  # LINE ID
    email = Column(String(100), nullable=False)                  # 學校 Email
    created_at = Column(DateTime, default=datetime.utcnow)

    current_dorm = relationship("CurrentDorm", uselist=False, back_populates="user")
    wishes = relationship("WishList", back_populates="user")

    __table_args__ = (
        CheckConstraint(gender.in_(['F', 'M']), name='check_gender'),
        CheckConstraint(degree.in_(['undergrad', 'grad']), name='check_degree'),
    )

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
    preferred_dorm = Column(String(20), nullable=False)  # 期望齋別
    preferred_room_type = Column(String(20), nullable=False)  # 期望房型
    preference_order = Column(Integer, nullable=False)   # 志願序
    status = Column(String(20), default="matching")      # 狀態

    user = relationship("User", back_populates="wishes")

# ==========================================
# 執行建立所有表格的主程式
# ==========================================
if __name__ == "__main__":
    print("正在初始化資料庫與建立表格...")
    Base.metadata.create_all(engine)
    print("資料庫建立成功！已生成 'dorm_exchange.db' 檔案。")