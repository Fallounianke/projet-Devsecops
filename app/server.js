const express = require('express');
const os = require('os');
const app = express();
const PORT = process.env.PORT || 3000;
const TMDB_TOKEN = process.env.TMDB_TOKEN;
const posterCache = new Map();
app.use(express.static('public'));
app.get('/health', (_req,res)=>res.json({status:'ok'}));
app.get('/api/info', (_req,res)=>res.json({podName:os.hostname(),platform:os.platform(),uptime:Math.floor(process.uptime()),memoryUsage:Math.round(process.memoryUsage().rss/1048576)+' MB',timestamp:new Date().toISOString()}));
app.get('/api/poster', async (req,res)=>{
  const title=String(req.query.title||'').trim().slice(0,120);
  const year=Number(req.query.year);
  if(!title || !Number.isInteger(year) || year<1880 || year>2100) return res.status(400).json({error:'Invalid movie'});
  if(!TMDB_TOKEN) return res.status(503).json({error:'TMDB_TOKEN is not configured'});
  const key=`${title}|${year}`;
  if(posterCache.has(key)) return res.json({poster:posterCache.get(key)});
  try {
    const params=new URLSearchParams({query:title,year:String(year),include_adult:'false'});
    const response=await fetch(`https://api.themoviedb.org/3/search/movie?${params}`,{headers:{Authorization:`Bearer ${TMDB_TOKEN}`,accept:'application/json'},signal:AbortSignal.timeout(8000)});
    if(!response.ok) throw new Error(`TMDB HTTP ${response.status}`);
    const data=await response.json();
    const normalized=s=>s.toLowerCase().replace(/[^a-z0-9]/g,'');
    const exact=data.results?.find(m=>normalized(m.title||'')===normalized(title)&&m.poster_path);
    const match=exact || data.results?.find(m=>m.poster_path && (m.release_date||'').startsWith(String(year)));
    const poster=match?.poster_path?`https://image.tmdb.org/t/p/w500${match.poster_path}`:null;
    posterCache.set(key,poster);
    return res.json({poster});
  }catch(err){console.error('TMDB poster lookup:',err.message);return res.status(502).json({error:'Poster service unavailable'});}
});
app.listen(PORT,()=>console.log(`CINERANK listening on ${PORT}`));
