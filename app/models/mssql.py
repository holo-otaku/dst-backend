from sqlalchemy import Column, String, Numeric
from models.shared import db


# PROD table
class Prod(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'PROD'
    PROD_NO = Column(String(19), primary_key=True)
    PROD_NAME = Column(String(200))
    FACT_NO = Column(String(8))
    PROD_R = Column(String(10))
    DOLR_RI = Column(Numeric(18, 8))
    DOLR_TI = Column(String(4))
    PROD_C = Column(Numeric(19, 6))
    PROD_CT = Column(Numeric(19, 6))
    KEYI_D = Column(String(8))
    LEAD_TIME = Column(Numeric(9, 4))
    FIZO_D = Column(String(8))
    PROD_STAT = Column(String(1))

    def __repr__(self):
        return f"<Prod(PROD_NO='{self.PROD_NO}', PROD_NAME='{self.PROD_NAME}', FACT_NO='{self.FACT_NO}', PROD_R='{self.PROD_R}', DOLR_RI={self.DOLR_RI}, DOLR_TI='{self.DOLR_TI}', PROD_C={self.PROD_C}, PROD_CT={self.PROD_CT}, KEYI_D='{self.KEYI_D}', LEAD_TIME={self.LEAD_TIME}, FIZO_D='{self.FIZO_D}', PROD_STAT='{self.PROD_STAT}')>"

# PRODR table
class Prodr(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'PRODR'
    PROD_R = Column(String(10), primary_key=True)
    PROD_RN = Column(String(20))

    def __repr__(self):
        return f"<Prodr(PROD_R='{self.PROD_R}', PROD_RN='{self.PROD_RN}')>"

# FACT table
class Fact(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'FACT'
    FACT_NO = Column(String(8), primary_key=True)
    FACT_NA = Column(String(20))
    FACT_NAME = Column(String(200))

    def __repr__(self):
        return f"<Fact(FACT_NO='{self.FACT_NO}', FACT_NA='{self.FACT_NA}', FACT_NAME='{self.FACT_NAME}')>"

# CUST table
class Cust(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'CUST'
    CUST_NO = Column(String(8), primary_key=True)
    CUST_NA = Column(String(20))
    CUST_NAME = Column(String(200))

    def __repr__(self):
        return f"<Cust(CUST_NO='{self.CUST_NO}', CUST_NA='{self.CUST_NA}', CUST_NAME='{self.CUST_NAME}')>"

# CUPD table
class Cupd(db.Model):
    __bind_key__ = 'mssql'
    __tablename__ = 'CUPD'
    CUST_NO = Column(String(8), primary_key=True)
    PROD_NO = Column(String(19), primary_key=True)
    CUPD_NO = Column(String(19))

    def __repr__(self):
        return f"<Cupd(CUST_NO='{self.CUST_NO}', PROD_NO='{self.PROD_NO}', CUPD_NO='{self.CUPD_NO}')>"
