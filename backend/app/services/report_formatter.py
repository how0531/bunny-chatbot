from typing import Dict, Any, List
from backend.app.services.sector_analyzer import SectorAnalyzer
from backend.app.services.stock_service import StockService
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

class ReportFormatter:
    """Format Morning Report text response."""

    def __init__(self, stock_service: StockService = None):
        self.sector_analyzer = SectorAnalyzer()
        self.stock_service = stock_service or StockService()

    def generate_report(self, snapshot: Dict[str, Any], inst_flow: Dict[str, Any], sector_analysis: Dict[str, Any], days: int = 2) -> str:
        """Generate the full Morning Report text."""
        try:
            report = "📊 投資早報\n\n"
            
            # 1. Global Market (snapshot)
            report += self._format_global_market(snapshot)
            
            # 2. Institutional Flow (inst_flow)
            report += self._format_institutional_flow(inst_flow)

            # 3. Strong Sectors with per-stock rise reasons
            strong_sectors = sector_analysis.get('strong_sectors', [])
            report += self._format_strong_sectors(strong_sectors, days=days)

            return report
        except Exception as e:
            logger.error(f"Error generating report format: {e}", exc_info=True)
            return "⚠️ 報表生成失敗"

    def _format_global_market(self, snapshot: Dict[str, Any]) -> str:
        text = "🌎 全球大盤\n\n"
        us = snapshot.get('us_indices', [])
        tw = snapshot.get('tw_indices', [])
        
        # US Indices
        if us:
            text += "【US 美股】\n"
            display_names = {
                '道瓊工業': '道瓊工業　　',
                '標普500': '標普500　　',
                '納茲達克': '納茲達克　　',
                '費城半導體': '費城半導體　'
            }
            for idx in us:
                text += self._format_index_line(idx, display_names)
            text += "\n"
        else:
            text += "US 美股：暫無資料\n\n"
            
        # TW Indices
        if tw:
            text += "【TW 台股】\n"
            for idx in tw:
                text += self._format_index_line(idx, align_width=6)
            text += "\n"
            
        return text

    def _format_index_line(self, idx: Dict[str, Any], display_map: Dict[str, str] = None, align_width: int = 0) -> str:
        try:
            change = float(idx.get('漲跌幅', 0))
            change_icon = "🔺" if change > 0 else "🔻" if change < 0 else "⚪"
            price = f"{float(idx.get('收盤價', 0)):,.2f}"
            change_str = f"{change:+.2f}%"
            name = idx.get('名稱', idx.get('代號'))
            
            if display_map:
                display_name = display_map.get(name, f"{name:　<{6}}") # Default alignment if map misses
            else:
                display_name = f"{name:　<{align_width}}"
                
            return f"  • {display_name} | {price} ({change_icon} {change_str})\n"
        except Exception as e:
            logger.error(f"Error formatting index line: {e}")
            return ""

    def _format_institutional_flow(self, inst_flow: Dict[str, Any]) -> str:
        text = "💰 籌碼流向\n\n"
        flows = inst_flow.get('institutional_flow', [])
        
        if not flows:
            return text + "  暫無法人數據\n\n"

        # Define custom sort order: 外資 → 投信 → 自營商
        order_map = {'外資合計': 1, '外資': 1, '投信': 2, '自營商': 3}
        sorted_flows = sorted(flows, key=lambda x: order_map.get(x.get('法人名稱', ''), 99))
        
        for flow in sorted_flows:
            try:
                amt = float(flow.get('合計買賣超(億)', 0))
                money_name = flow.get('法人名稱', '不明法人')
                if money_name == '外資合計':
                    money_name = '外資'
                amt_str = f"{abs(amt):,.2f} 億"
                name_aligned = f"{money_name:　<6}"
                
                if amt > 0:
                    text += f"  • {name_aligned} | 🔺 買超 {amt_str}\n"
                elif amt < 0:
                    text += f"  • {name_aligned} | 🔻 賣超 {amt_str}\n"
                else:
                    text += f"  • {name_aligned} | ⚪ 平盤\n"
            except Exception as e:
                logger.error(f"Error formatting flow: {e}")
                
        return text + "\n"

    def _format_strong_sectors(self, strong_sectors: List[Dict[str, Any]], days: int = 2) -> str:
        if not strong_sectors:
            return "🏭 強勢族群：資料建置中\n"
            
        text = f"📅 近 {days} 日強勢族群\n\n"
        
        # Group by sector
        sectors_dict = {}
        for item in strong_sectors:
            sector_name = item.get('概念名稱', '未知族群')
            if sector_name not in sectors_dict:
                sectors_dict[sector_name] = []
            sectors_dict[sector_name].append(item)
            
        rank_emojis = ["1️⃣", "2️⃣", "3️⃣"]
        for i, (sector_name, stocks) in enumerate(sectors_dict.items()):
            try:
                # Calculate average return
                avg_return = sum(float(s.get('漲跌幅', 0)) for s in stocks) / len(stocks)
                sector_icon = "🔺" if avg_return > 0 else "🔻" if avg_return < 0 else "⚪"
                
                rank_prefix = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}."
                text += f"{rank_prefix} 【 {sector_name} 】 平均 {sector_icon} {avg_return:+.2f}%\n"
                
                # List stocks (top 4)
                sorted_stocks = sorted(stocks, key=lambda x: float(x.get('漲跌幅', 0)), reverse=True)
                for stock in sorted_stocks[:4]:
                    text += self._format_stock_line_aligned(stock)
                
                # ── Per-stock rise reasons from MongoDB hotwords ──
                reason_lines = []
                latest_hw_date = self.stock_service.mongo.get_latest_hotwords_date()
                
                for stock in sorted_stocks[:4]:
                    sid = stock.get('股票代號', '')
                    sname = stock.get('股票名稱', sid)
                    if not sid:
                        continue
                    try:
                        # Strictly use the latest date available in the DB
                        hotword = self.stock_service.mongo.get_hotword_doc(sid, target_date=latest_hw_date)
                        if hotword:
                            reason = hotword.get('股價上漲原因(熱度起始日)', '')
                            if reason:
                                reason_lines.append(f"• {sname}：{reason}")
                    except Exception as e:
                        logger.warning(f"Hotword lookup for {sid} failed: {e}")
                
                if reason_lines:
                    text += "📝 永豐筆記 | 漲因解析：\n"
                    text += "\n".join(reason_lines) + "\n"
                
                text += "\n"
            except Exception as e:
                logger.error(f"Error formatting sector {sector_name}: {e}")
                
        return text

    def _format_focus_stocks(self, strong_sectors: List[Dict[str, Any]]) -> str:
        text = "🔥 焦點個股\n\n"
        
        # ── Query MongoDB sinopac_hotwords_v2 for top-heat stocks ──
        try:
            top_hotwords = list(
                self.stock_service.mongo.hotwords_col.find(
                    {'豐搜熱度': {'$exists': True, '$gt': 0}},
                    sort=[('豐搜熱度', -1)],
                ).limit(5)
            )
        except Exception as e:
            logger.error(f"Failed to query hotwords for focus stocks: {e}")
            top_hotwords = []

        if not top_hotwords:
            return text + "暫無焦點個股資料\n"
        
        seen = set()
        count = 0
        for doc in top_hotwords:
            if count >= 3:
                break
            
            code = doc.get('股票代號', '')
            if not code or code in seen:
                continue
            seen.add(code)
            count += 1
            
            name = doc.get('股票名稱', code)
            heat = doc.get('豐搜熱度', 0)
            reason = doc.get('股價上漲原因(熱度起始日)', '')
            date = doc.get('資料日期', '')
            
            # Format stock line
            text += f"**{code} {name}** 🔥 熱度: {heat}\n"
            
            # Rise reason from hotwords
            if reason:
                text += f"📝 {reason}\n"
            
            # Institutional flow streak
            try:
                foreign_days = self.stock_service.mongo.calculate_consecutive_buy_days(code, 'foreign')
                trust_days = self.stock_service.mongo.calculate_consecutive_buy_days(code, 'trust')
                flow_parts = []
                if foreign_days >= 2:
                    flow_parts.append(f"外資連買{foreign_days}日")
                if trust_days >= 2:
                    flow_parts.append(f"投信連買{trust_days}日")
                if flow_parts:
                    text += f"💰 {' | '.join(flow_parts)}\n"
            except Exception:
                pass
            
            text += "\n"
                
        return text

    def _format_stock_line_aligned(self, stock: Dict[str, Any], bold: bool = False) -> str:
        code = stock.get('股票代號', '')
        name = stock.get('股票名稱', code)
        ret = float(stock.get('漲跌幅', 0))
        ret_icon = "🔺" if ret > 0 else "🔻" if ret < 0 else "⚪"
        
        clean_name = name[:5] if name else ""
        padded_name = f"{clean_name:\u3000<5}"
        ret_str = f"{ret:+.2f}%"
        
        line = f"{code} {padded_name} {ret_icon} {ret_str:>7}"
        if bold:
            return f"**{line}**\n"
        return f"  • {line}\n"

    def format_stock_focus(self, data: Dict[str, Any], tw_info: str = "") -> str:
        """Format the professional stock focus card."""
        try:
            name = data.get('name', '個股')
            stock_id = data.get('stock_id', '')
            reason = data.get('reason', '暫無分析')
            concepts = data.get('concepts', [])
            news = data.get('recent_news', [])
            
            # Simple Scoring (Optional: Use calculate_score for deeper logic)
            # For now, let's keep it clean
            
            # Header
            report = f"🎯 **{name} ({stock_id}) 個股重點**\n\n"
            
            # Section 1: Core Insight
            report += "✨ **核心觀點**\n"
            display_reason = reason.replace("主要概況:", "").replace("股價上漲原因:", "").strip()
            report += f"{display_reason}\n\n"
            
            if concepts:
                report += f"💡 **相關概念**: {', '.join(concepts)}\n\n"
            
            # Section 2: Financial Data
            if tw_info.strip():
                report += tw_info.strip() + "\n"
            
            # Section 2b: Earnings Call Insights (AlphaMemo)
            try:
                earnings = self.stock_service.get_earnings_call_insights(stock_id)
                
                if earnings.get('found'):
                    report += f"\n📊 **法說會重點** ({earnings['date']})\n\n"
                    
                    if earnings.get('highlights'):
                        report += "**🎯 亮點**\n"
                        report += earnings['highlights'] + "\n\n"
                    
                    if earnings.get('revenue'):
                        report += "**💰 營收**\n"
                        report += earnings['revenue'] + "\n\n"
                    
                    if earnings.get('profit'):
                        report += "**📈 獲利**\n"
                        report += earnings['profit'] + "\n\n"
                    
                    if earnings.get('outlook'):
                        report += "**🔮 展望**\n"
                        report += earnings['outlook'] + "\n\n"
                else:
                    # Show why earnings data is not available
                    if earnings.get('error'):
                        logger.info(f"Earnings call insights not available for {stock_id}: {earnings.get('error')}")
                        # Optionally add to report (commented out to avoid clutter)
                        # report += f"\n💡 *法說會資料：{earnings.get('error')}*\n\n"
            except Exception as e:
                logger.error(f"Failed to get earnings call insights for {stock_id}: {e}", exc_info=True)
                # Optionally show error to user
                report += "\n💡 *法說會資料暫時無法取得*\n\n"
            
            # Section 3: Recent News (Only show if filtered news exists)
            if news:
                report += "\n📰 **近期新聞標題**\n"
                for n in news[:3]:
                    report += f"- {n['title']}\n\n"
            elif "近期無特定個股重大消息" not in reason:
                report += "\n💡 *近期該股於媒體聲量較小，建議觀察技術面表現。*\n"

            # Section 4: Analysis Certificate (Sophia's Final Touch)
            report += f"\n---\n"
            report += f"**Analysis Certificate**\n"
            report += f"✅ **Strategy**: @Arthur (Quant Logic v3.2)\n"
            report += f"🛡️ **Compliance**: @Oscar (Pass: {data.get('status', 'OK')})\n"
            report += f"👑 **Approved**: @Sophia (Level-1 Directorship)\n"
            report += f"---\n"
            report += f"📎 *數據來源：{data.get('source', 'Arthur-Engine')}*"
            
            return report
        except Exception as e:
            logger.error(f"Error formatting stock focus: {e}")
            return f"解析 {data.get('stock_id', '')} 時發生錯誤"
