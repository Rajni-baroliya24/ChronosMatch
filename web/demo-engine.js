/* Browser-only simulator. The Python edition uses the Flask API instead. */
(function(root){
'use strict';
const symbols={AAPL:['Apple Inc.',18924],MSFT:['Microsoft',42870],NVDA:['NVIDIA',13245],TSLA:['Tesla',24850]};
const defaults={max_quantity:10000,max_notional:1000000,paused:false};
const clock=()=>new Date().toISOString();
const active=o=>['OPEN','PARTIAL'].includes(o.status)&&o.remaining>0;
const number=(v,label,min,max)=>{if(!Number.isSafeInteger(v)||v<min||v>max)throw Error(`${label} must be an integer from ${min.toLocaleString()} to ${max.toLocaleString()}`);return v};
class DemoEngine{
 constructor(storage=null,{seed=true,restore=true,sampleLimit=2000}={}){
  this.sampleLimit=sampleLimit;this.storage=storage;this.key='chronosmatch-studio-v2';this.persistent=!!storage;this.resetMemory();
  if(restore&&storage){try{const saved=JSON.parse(storage.getItem(this.key)||'null');if(saved&&saved.version===2&&Array.isArray(saved.orders)&&Array.isArray(saved.trades)&&saved.risk&&Number.isSafeInteger(saved.nextId)){Object.assign(this,{orders:saved.orders,trades:saved.trades,risk:saved.risk,nextId:saved.nextId,benchmarks:saved.benchmarks||[]});this.rebuild();}}catch(e){this.persistent=false;}}
  if(seed&&!this.orders.length)this.seed();
 }
 resetMemory(){this.orders=[];this.trades=[];this.risk={...defaults};this.nextId=1;this.latencies=[];this.benchmarks=[];this.books={};this.byId=new Map();}
 rebuild(){this.books={};this.byId=new Map();for(const o of this.orders){this.byId.set(o.id,o);if(active(o))this.addResting(o)}}
 book(symbol){return this.books[symbol]||(this.books[symbol]={BUY:new Map(),SELL:new Map()})}
 addResting(o){const levels=this.book(o.symbol)[o.side];if(!levels.has(o.price_ticks))levels.set(o.price_ticks,[]);levels.get(o.price_ticks).push(o)}
 save(){if(!this.storage)return;try{this.storage.setItem(this.key,JSON.stringify({version:2,orders:this.orders,trades:this.trades,risk:this.risk,nextId:this.nextId,benchmarks:this.benchmarks}));this.persistent=true}catch(e){this.persistent=false}}
 depth(symbol){const b=this.book(symbol);const result={bids:[],asks:[]};for(const [side,key]of [['BUY','bids'],['SELL','asks']]){for(const [price,queue]of b[side]){const quantity=queue.reduce((a,o)=>a+o.remaining,0);if(quantity)result[key].push({price:price/100,quantity})}result[key].sort((a,c)=>side==='BUY'?c.price-a.price:a.price-c.price)}return result}
 best(symbol,side){const levels=this.book(symbol)[side];if(!levels.size)return null;let best=side==='BUY'?-Infinity:Infinity;for(const p of levels.keys())best=side==='BUY'?Math.max(best,p):Math.min(best,p);return best}
 seed(){for(const [index,[symbol,[,base]]]of Object.entries(symbols).entries()){for(let level=1;level<=8;level++){for(const side of ['BUY','SELL']){this.submitInternal({symbol,side,type:'LIMIT',price_ticks:base+(side==='BUY'?-1:1)*level*4,quantity:140+((index+level)*137)%700},'LIQUIDITY',false)}}}this.save()}
 submitInternal(data,source='MANUAL',persist=true){
  const o={id:this.nextId++,symbol:data.symbol,side:data.side,type:data.type,price_ticks:data.price_ticks,price:data.price_ticks/100,quantity:data.quantity,remaining:data.quantity,filled:0,status:'OPEN',source,time:clock()};
  this.orders.push(o);this.byId.set(o.id,o);
  const start=performance.now(),opposite=this.book(o.symbol)[o.side==='BUY'?'SELL':'BUY'];
  while(o.remaining&&opposite.size){const p=this.best(o.symbol,o.side==='BUY'?'SELL':'BUY');if(o.side==='BUY'?o.price_ticks<p:o.price_ticks>p)break;const queue=opposite.get(p),r=queue[0],qty=Math.min(o.remaining,r.remaining);o.remaining-=qty;o.filled+=qty;r.remaining-=qty;r.filled+=qty;r.status=r.remaining?'PARTIAL':'FILLED';o.status=o.remaining?'PARTIAL':'FILLED';this.trades.push({id:this.trades.length+1,symbol:o.symbol,price:p/100,quantity:qty,buy_order_id:o.side==='BUY'?o.id:r.id,sell_order_id:o.side==='SELL'?o.id:r.id,side:o.side,time:o.time});if(!r.remaining){queue.shift();if(!queue.length)opposite.delete(p)}}
  if(o.remaining){if(o.type==='MARKET'){o.status='EXPIRED';o.remaining=0}else this.addResting(o)}
  this.latencies.push((performance.now()-start)*1000);if(this.latencies.length>this.sampleLimit)this.latencies.shift();if(persist)this.save();return o;
 }
 submit(data,source='MANUAL'){
  if(this.risk.paused)throw Error('Engine is paused. Resume it in Risk controls.');
  const {symbol,side,quantity}=data,type=data.type||'LIMIT';
  if(typeof symbol!=='string'||!Object.hasOwn(symbols,symbol))throw Error('Choose a supported symbol');
  if(!['BUY','SELL'].includes(side)||!['LIMIT','MARKET'].includes(type))throw Error('Choose BUY or SELL, and LIMIT or MARKET');
  number(quantity,'Quantity',1,this.risk.max_quantity);
  let ticks,marketNotional;
  if(type==='MARKET'){
    const depth=this.depth(symbol)[side==='BUY'?'asks':'bids'];
    if(!depth.length)throw Error('No opposing liquidity. Add a limit order first.');
    ticks=Math.round(depth[depth.length-1].price*100);
    let remaining=quantity;marketNotional=0;
    for(const level of depth){
      const filled=Math.min(remaining,level.quantity);
      marketNotional+=Math.round(level.price*100)*filled;
      remaining-=filled;
      if(!remaining)break;
    }
  }else{
    const raw=String(data.price??'');
    if(!/^\d+(\.\d{1,2})?$/.test(raw)||+raw<=0||+raw>1000000)throw Error('Price must be $0.01–$1,000,000, with at most two decimals');
    ticks=Math.round(+raw*100);
  }
  const notional=type==='MARKET'?marketNotional:ticks*quantity;
  if(notional>this.risk.max_notional*100)throw Error('Order exceeds the maximum order notional in Risk controls');
  return this.submitInternal({symbol,side,type,price_ticks:ticks,quantity},source)
 }
 cancel(id){const o=this.byId.get(id);if(!o||!active(o))throw Error('Order is already closed or does not exist');const levels=this.book(o.symbol)[o.side],queue=levels.get(o.price_ticks);const at=queue.indexOf(o);queue.splice(at,1);if(!queue.length)levels.delete(o.price_ticks);o.status='CANCELLED';o.remaining=0;this.save();return o}
 tick(symbol){if(!Object.hasOwn(symbols,symbol))throw Error('Choose a supported symbol');if(this.risk.paused)throw Error('Engine is paused. Resume it in Risk controls.');const side=Math.random()<.5?'BUY':'SELL';if(this.best(symbol,side==='BUY'?'SELL':'BUY')===null)this.submitInternal({symbol,side:side==='BUY'?'SELL':'BUY',type:'LIMIT',price_ticks:symbols[symbol][1],quantity:200},'LIQUIDITY',false);return this.submit({symbol,side,type:'MARKET',quantity:Math.floor(Math.random()*Math.min(76,this.risk.max_quantity))+1},'DEMO')}
 updateRisk(data){const updates={};for(const [key,max]of [['max_quantity',1000000],['max_notional',100000000]])if(key in data)updates[key]=number(data[key],key,1,max);if('paused'in data){if(typeof data.paused!=='boolean')throw Error('paused must be true or false');updates.paused=data.paused}Object.assign(this.risk,updates);this.save();return this.risk}
 reset(){this.resetMemory();this.seed()}
 snapshot(symbol='AAPL'){
  if(!Object.hasOwn(symbols,symbol))throw Error('Choose a supported symbol');const depth=this.depth(symbol),trades=this.trades.filter(t=>t.symbol===symbol),orders=this.orders.filter(o=>o.symbol===symbol),volume=trades.reduce((a,t)=>a+t.price*t.quantity,0),shares=trades.reduce((a,t)=>a+t.quantity,0),lat=[...this.latencies].sort((a,b)=>a-b),p=q=>lat.length?Math.round(lat[Math.floor(q*(lat.length-1))]*100)/100:null;
  return{symbol,name:symbols[symbol][0],mode:'browser',risk:{...this.risk},watchlist:Object.entries(symbols).map(([s,[name,base]])=>{const trade=this.trades.findLast(t=>t.symbol===s),price=trade?trade.price:base/100;return{symbol:s,name,price,change:Math.round((price/(base/100)-1)*10000)/100}}),reference:symbols[symbol][1]/100,...depth,best_bid:depth.bids[0]?.price??null,best_ask:depth.asks[0]?.price??null,last_price:trades.at(-1)?.price??symbols[symbol][1]/100,orders:orders.slice().reverse(),trades:trades.slice(-500).reverse(),history:trades.slice(-200),active_orders:orders.filter(active).length,total_orders:orders.length,total_trades:trades.length,matched_shares:shares,volume:Math.round(volume*100)/100,vwap:shares?Math.round(volume/shares*100)/100:null,latency:{median:p(.5),p95:p(.95),p99:p(.99),samples:lat.length},benchmarks:this.benchmarks.slice(0,8)}
 }
 benchmark(count=5000){number(count,'Benchmark count',100,20000);const isolated=new DemoEngine(null,{seed:false,restore:false,sampleLimit:Infinity});let trades=0;const start=performance.now();for(let i=0;i<count;i++){isolated.submitInternal({symbol:'AAPL',side:i%2?'BUY':'SELL',type:'LIMIT',price_ticks:10000,quantity:1},'BENCHMARK',false)}const elapsed=performance.now()-start,samples=isolated.latencies.slice().sort((a,b)=>a-b),p=q=>Math.round(samples[Math.floor(q*(samples.length-1))]*100)/100;trades=isolated.trades.length;const result={count,throughput:Math.round(count/(elapsed/1000)),median:p(.5),p95:p(.95),p99:p(.99),trades,elapsed_ms:Math.round(elapsed*100)/100,mode:'browser',time:clock(),scenario:'Alternating same-price limit orders; isolated in-memory browser engine; excludes rendering and persistence.'};this.benchmarks.unshift(result);this.benchmarks=this.benchmarks.slice(0,8);this.save();return result}
}
root.ChronosDemoEngine=DemoEngine;
if(typeof module!=='undefined')module.exports={DemoEngine,symbols};
})(typeof window!=='undefined'?window:globalThis);
