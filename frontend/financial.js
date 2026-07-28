(function (root) {
  function navMetrics(rows, riskFree) {
    const valid = (rows || []).filter(r => r.n > 0).sort((a, b) => a.dk - b.dk);
    if (valid.length < 3) return null;
    const returns = valid.slice(1).map((r, i) => r.n / valid[i].n - 1), mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const vol = Math.sqrt(returns.reduce((s, r) => s + (r - mean) ** 2, 0) / returns.length) * Math.sqrt(52);
    let peak = valid[0].n, mdd = 0; const drawdowns = valid.map(r => { peak = Math.max(peak, r.n); const d = (peak-r.n)/peak; mdd = Math.max(mdd,d); return -d; });
    const years = (new Date(valid.at(-1).d.replaceAll('/','-')) - new Date(valid[0].d.replaceAll('/','-'))) / 86400000 / 365.2425;
    const annualReturn = years > 0 ? (valid.at(-1).n / valid[0].n) ** (1 / years) - 1 : 0;
    return {mdd:-mdd, volatility:vol, annualReturn, sharpe:vol?(annualReturn-riskFree)/vol:0, riskFree, years, drawdowns, warning:years<1};
  }
  function goalScenarios(current, monthly, target=100000000) { return [['保守',.03],['中性',.07],['樂觀',.12]].map(([label,rate])=>{const r=(1+rate)**(1/12)-1;let value=current,months=0;while(value<target&&months<1200){value=value*(1+r)+monthly;months++;}return {label,rate,months:value>=target?months:null};}); }
  function nextTradingDate(date, prices) { const d=new Date(date.replaceAll('/','-')+'T00:00:00'); for(let i=0;i<=7;i++){const x=new Date(d);x.setDate(d.getDate()+i);const k=x.getFullYear()+'/'+String(x.getMonth()+1).padStart(2,'0')+'/'+String(x.getDate()).padStart(2,'0');if(prices[k]>0)return k;}return null; }
  root.Financial = {navMetrics, goalScenarios, nextTradingDate};
})(window);
