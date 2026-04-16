import pandas as pd
import yfinance as yf
import numpy as np
import streamlit as st
from datetime import datetime
import warnings

# --- 1. 基础配置 ---
warnings.filterwarnings('ignore')
st.set_page_config(page_title="Alpha Option 终极诊断系统", layout="wide")

# --- 2. 核心诊断引擎 ---
def diagnostic_engine_ultimate(ticker):
    try:
        ticker = ticker.strip().upper()
        tk = yf.Ticker(ticker)

        # 基础数据抓取
        hist = tk.history(period="1y")
        if hist.empty: return None
        price = hist['Close'].iloc[-1]

        # 波动率计算
        log_rets = np.log(hist['Close'] / hist['Close'].shift(1))
        current_hv = log_rets.tail(30).std() * np.sqrt(252)
        avg_hv = log_rets.std() * np.sqrt(252) 

        # 期权链分析
        exps = tk.options
        if not exps: return None
        target_date = exps[0] 
        opt = tk.option_chain(target_date)
        dte = max((datetime.strptime(target_date, '%Y-%m-%d') - datetime.now()).days, 1)

        # 关键指标计算
        opt.calls['diff'] = abs(opt.calls['strike'] - price)
        atm_iv = opt.calls.sort_values('diff').iloc[0]['impliedVolatility']
        pcr = opt.puts['volume'].sum() / (opt.calls['volume'].sum() + 1e-5)

        ivp = (atm_iv / (avg_hv * 1.5)) * 100
        ivp = min(max(ivp, 5), 95)
        move_range = price * atm_iv * np.sqrt(dte / 365)
        
        # Skew 计算简化版
        skew = opt.puts.iloc[-1]['impliedVolatility'] - opt.calls.iloc[-1]['impliedVolatility']

        # 逻辑判定
        score = 50
        advice = ""
        if pcr < 0.28 and ivp < 35:
            score, advice = 95, "🔴 极端诱多：PCR极低且保费廉价。建议买入 Put 对冲。"
        elif pcr > 1.25 and ivp > 65:
            score, advice = 90, "🟢 恐慌极值：IVP高，适合 Sell Put 赚取权利金。"
        elif atm_iv < current_hv * 0.72:
            score, advice = 88, "💎 价值洼地：IV低于HV。适合买入跨式或长线Call。"
        elif skew > 0.18:
            score, advice = 78, "🟠 机构避险：Skew大幅转正。警惕回调风险。"
        elif skew < -0.06 and ivp > 55:
            score, advice = 82, "⚠️ 狂热陷阱：Call Skew异常。严禁追高。"
        elif pcr > 0.85 and ivp < 40:
            score, advice = 65, "⚪ 阴跌磨底：活跃度低，不宜过早重仓抄底。"
        else:
            score, advice = 50, "🔘 均衡状态：定价合理，建议维持现状。"

        return {
            "代码": ticker, "现价": round(price, 2), "HV(30D)": f"{current_hv:.1%}",
            "ATM_IV": f"{atm_iv:.1%}", "IVP": f"{ivp:.1f}%", "PCR": round(pcr, 3),
            "Skew": round(skew, 2), "预期涨跌幅": f"±${move_range:.2f}",
            "综合得分": score, "策略建议": advice
        }
    except:
        return None

# --- 3. Streamlit 界面设计 ---
st.title("🧠 ALPHA OPTION 终极诊断系统")
st.markdown("---")

tab1, tab2 = st.tabs(["自动扫描 (Watchlist)", "手动诊断 (Custom)"])

# 功能一：自动扫描 (建议在美股开盘 1 小时后观察，此时期权定价最稳定)
with tab1:
    st.header("📋 LzkWatchlist 定时扫描")
    if st.button("开始扫描 Watchlist"):
        try:
            watchlist_df = pd.read_csv("LzkWatchlist.csv")
            # 假设 CSV 中第一列是 Symbol
            tickers = watchlist_df.iloc[:, 0].tolist()
            
            with st.spinner('正在分析 Watchlist 标的...'):
                results = [diagnostic_engine_ultimate(t) for t in tickers]
                results = [r for r in results if r is not None]
                
                if results:
                    df = pd.DataFrame(results).sort_values("综合得分", ascending=False)
                    st.table(df) # 使用 table 显示静态美化表格
                else:
                    st.error("未找到有效的期权数据。")
        except FileNotFoundError:
            st.warning("请确保根目录下存在 LzkWatchlist.csv 文件。")

# 功能二：手动输入
with tab2:
    st.header("🔍 手动标的诊断")
    user_input = st.text_input("请输入股票代码（多个请用空格分隔）", "TSLA NVDA RKLB")
    if st.button("开始诊断"):
        tickers = [t.strip().upper() for t in user_input.replace(',', ' ').split()][:10]
        with st.spinner('分析中...'):
            results = [diagnostic_engine_ultimate(t) for t in tickers]
            results = [r for r in results if r is not None]
            
            if results:
                df = pd.DataFrame(results).sort_values("综合得分", ascending=False)
                st.dataframe(df.style.background_gradient(subset=['综合得分'], cmap='RdYlGn'))
            else:
                st.error("请输入有效的期权标的代码。")

st.sidebar.info("💡 **观察建议**：推荐在美股开盘 1 小时（美东 10:30 AM）后运行，此时 IV 的隔夜波动已平复。")
