"use strict";

const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const State={bootstrap:null,session:null,current:null,setup:{},score:0,sound:true,view:"games",topic:"animal",items:[],visible:30,topicCache:new Map(),cleanup:null,timer:null,remaining:0,timerMinutes:5};
const UI={games:$("#gamesView"),library:$("#libraryView"),design:$("#designView"),game:$("#gameView"),grid:$("#gameGrid"),stage:$("#stage"),modal:$("#setupModal"),detail:$("#detailModal"),topics:$("#topicTabs"),libraryGrid:$("#libraryGrid"),search:$("#librarySearch"),toast:$("#toast")};
const META={
  "listen-image-en":{group:"learning",color:"#1b7f8d",desc:"Nghe phát âm tiếng Anh và chọn đúng hình."},
  "listen-image-vi":{group:"learning",color:"#25755e",desc:"Nghe tên tiếng Việt và nhận biết hình ảnh."},
  puzzle:{group:"thinking",color:"#795aa8",desc:"Quan sát mẫu và ghép các mảnh về đúng vị trí."},
  sudoku:{group:"thinking",color:"#9b6b35",desc:"Điền số theo hàng, cột và vùng không lặp lại."},
  "image-answer":{group:"learning",color:"#355e9b",desc:"Nhìn hình và chọn tên gọi chính xác."},
  count:{group:"learning",color:"#9b7135",desc:"Đếm số lượng vật thể và chọn đáp án."},
  "alphabet-en":{group:"learning",color:"#8d3f6e",desc:"Học mặt chữ và cách đọc bảng chữ cái tiếng Anh."},
  "alphabet-vi":{group:"learning",color:"#436eaa",desc:"Học bảng chữ cái tiếng Việt cùng dấu đặc trưng."},
  memory:{group:"thinking",color:"#6152a5",desc:"Lật thẻ, ghi nhớ và tìm các cặp giống nhau."},
  bomber:{group:"thinking",color:"#9a4941",desc:"Dò mìn trên máy tính, mở ô an toàn và đánh dấu vị trí có bom."},
  "hidden-object":{group:"thinking",color:"#437f67",desc:"Tìm đủ các vật mẫu đang ẩn trong bức tranh."},
  "tic-tac-toe":{group:"thinking",color:"#59647f",desc:"Cờ caro vô hạn cho hai người, kéo bàn cờ và nối năm quân để thắng."},
  colors:{group:"learning",color:"#9a3f5d",desc:"Nhận biết, nghe tên và luyện phản xạ với màu sắc."},
  "space-shooter":{group:"action",color:"#3a4c9b",desc:"Phi thuyền tự động bắn, nhặt vật phẩm, tem thưởng và nâng cấp."},
  "math-basic":{group:"learning",color:"#367a74",desc:"Luyện cộng, trừ và so sánh số cơ bản."},
  "math-advanced":{group:"learning",color:"#77548e",desc:"Luyện nhân, chia và bài toán nhiều bước."},
  "match-transport":{group:"learning",color:"#2f718c",desc:"Nối phương tiện với đường bộ, đường thủy hoặc hàng không."},
  "match-habitat":{group:"learning",color:"#4d7f48",desc:"Nối động vật với môi trường sống phù hợp."}
};
const TOPIC_ICONS={animal:"🦁",transport:"🚗",plant:"🍎",object:"🎸",flag:"🏳️",number:"123","alphabet-en":"ABC","alphabet-vi":"ĂÂ","environment":"🌍"};
const DESIGN=[["✦","Icon","Biểu tượng nền trong suốt cho game và điều hướng."],["♟","Model & NPC","Nhân vật, vật thể và mẫu tham khảo."],["▦","Map","Bản đồ, địa hình và bố cục màn chơi."],["🏆","Trophy","Huy hiệu, cúp và phần thưởng."],["▶","Animation & GIF","Chuyển động, hiệu ứng và trạng thái."],["▣","Frame","Khung ảnh, bảng thông tin và thẻ học."],["◐","Theme","Màu sắc, kiểu chữ và bộ giao diện."],["⬇","PNG trong suốt","Bộ ảnh mới không nền, dùng lại đa mục đích."]];
const escapeHtml=(v="")=>String(v).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const shuffle=input=>{const a=[...input];for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a};
const asset=p=>p?"/resource/"+p:"";
const thumb=p=>p?"/thumb/"+p:"";
const showToast=text=>{UI.toast.textContent=text;UI.toast.classList.add("show");clearTimeout(showToast.t);showToast.t=setTimeout(()=>UI.toast.classList.remove("show"),1800)};
const setScore=n=>{$("#score").textContent=State.score=n};
const reward=(n=10,text="Chính xác!")=>{setScore(State.score+n);showToast(text+" · +"+n)};
const miss=(text="Thử lại nhé!")=>showToast(text);
const makeUtterance=(text,lang="vi-VN")=>{const u=new SpeechSynthesisUtterance(text);u.lang=lang;u.rate=lang.startsWith("en")?.78:.82;const voice=speechSynthesis.getVoices().find(v=>v.lang.toLowerCase().startsWith(lang.slice(0,2).toLowerCase()));if(voice)u.voice=voice;return u};
const speak=(text,lang="vi-VN")=>{if(!State.sound||!text)return;speechSynthesis.cancel();speechSynthesis.speak(makeUtterance(text,lang))};
const speakAsync=(text,lang="vi-VN")=>new Promise(resolve=>{if(!State.sound||!text)return resolve();speechSynthesis.cancel();const u=makeUtterance(text,lang),done=()=>resolve();u.onend=done;u.onerror=done;speechSynthesis.speak(u);setTimeout(done,2600)});
const allowedGame=id=>!!State.session?.games?.some(g=>g.id===id);
const currentSessionGame=id=>State.session?.games?.find(g=>g.id===id);

async function fetchSession(){
  const token=new URLSearchParams(location.search).get("session");
  if(!token)return null;
  try{
    const response=await fetch((window.GOT_PORTAL_ORIGIN||"https://thienha.io.vn")+"/api/game-of-thien/sessions/"+encodeURIComponent(token),{cache:"no-store"});
    const data=await response.json();if(!response.ok||!data.ok)throw Error(data.message||"Phiên không hợp lệ");
    return {token,games:data.config.games||[],expiresAt:data.expires_at,status:data.status};
  }catch(error){showToast(error.message);return {error:error.message,games:[]}}
}

async function init(){
  try{
    const [bootstrap,session]=await Promise.all([fetch("/api/bootstrap").then(r=>r.json()),fetchSession()]);
    State.bootstrap=bootstrap;State.session=session;
    if(["127.0.0.1","localhost"].includes(location.hostname)&&new URLSearchParams(location.search).get("preview")==="1"){
      State.session={games:bootstrap.games.map(g=>({id:g.id,duration_minutes:5})),status:"preview"};
    }
    $("#resourceCount").textContent=bootstrap.manifest?.counts?.items||"500+";
    renderSession();renderGames();renderTopics();renderDesign();bind();
  }catch(error){UI.grid.innerHTML='<div class="result-box"><h2>Không tải được dữ liệu</h2><p>'+escapeHtml(error.message)+'</p></div>'}
}
function bind(){
  $$(".nav-button").forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  $$(".filter").forEach(b=>b.onclick=()=>{$$(".filter").forEach(x=>x.classList.toggle("active",x===b));renderGames(b.dataset.filter)});
  $("#soundButton").onclick=()=>{$("#soundButton").textContent=(State.sound=!State.sound)?"🔊":"🔇";if(!State.sound)speechSynthesis.cancel()};
  $("#backButton").onclick=()=>switchView("games");
  $("#startButton").onclick=startCurrentGame;
  $$("[data-close]").forEach(b=>b.onclick=()=>$("#"+b.dataset.close).classList.remove("show"));
  UI.search.oninput=renderLibrary;
  $("#loadMore").onclick=()=>{State.visible+=30;renderLibrary()};
  $("#randomItem").onclick=()=>{const list=filteredItems();if(list.length)openDetail(list[Math.floor(Math.random()*list.length)])};
  $("#speakVi").onclick=()=>speak(State.detailItem?.viName,"vi-VN");
  $("#speakEn").onclick=()=>speak(State.detailItem?.enName,"en-US");
  $("#detailEnglish").onclick=()=>speak(State.detailItem?.enName,"en-US");
  $("#nextDetail").onclick=()=>{const list=filteredItems(),i=list.indexOf(State.detailItem);if(list.length)openDetail(list[(i+1)%list.length])};
}
function renderSession(){
  const chip=$("#sessionChip"),notice=$("#sessionNotice");
  if(State.session&&!State.session.error&&State.session.games.length){chip.textContent=State.session.games.length+" trò · phiên đang hoạt động";chip.className="session-chip active";notice.hidden=true}
  else{chip.textContent=State.session?.error||"Chưa mở phiên chơi";chip.className="session-chip error";notice.hidden=false}
}
function switchView(view){
  stopGame();State.view=view;
  [UI.games,UI.library,UI.design,UI.game].forEach(x=>x.classList.remove("active"));
  ({games:UI.games,library:UI.library,design:UI.design,game:UI.game}[view]||UI.games).classList.add("active");
  $$(".nav-button").forEach(b=>b.classList.toggle("active",b.dataset.view===view));
  if(view==="library"&&!State.items.length)loadTopic(State.topic);
  scrollTo({top:0,behavior:"smooth"});
}
function renderGames(filter="all"){
  UI.grid.innerHTML="";
  State.bootstrap.games.filter(g=>g.enabled!==false&&(filter==="all"||META[g.id]?.group===filter)).forEach((g,i)=>{
    const locked=!allowedGame(g.id),m=META[g.id]||{group:"learning",color:"#35677d",desc:"Một thử thách đang chờ bạn."},b=document.createElement("button");
    b.className="game-card"+(locked?" locked":"");b.style.setProperty("--card",m.color);
    b.innerHTML='<span class="game-index">'+String(i+1).padStart(2,"0")+' · '+m.group.toUpperCase()+'</span><span class="game-icon">'+escapeHtml(g.icon||"🎮")+"</span><h3>"+escapeHtml(g.name.vi)+"</h3><p>"+escapeHtml(m.desc)+'</p><footer>'+(locked?"CHƯA CÓ TRONG PHIÊN":"CHƠI NGAY")+' <span>'+(locked?"🔒":"→")+"</span></footer>";
    b.onclick=()=>locked?showToast("Hãy chọn trò này khi mở phiên từ Thiên Hạ"):openSetup(g);UI.grid.appendChild(b)
  })
}
function openSetup(game){
  State.current=game;State.setup={difficulty:"easy",topic:State.bootstrap.topics[0]?.id||"animal"};
  $("#setupIcon").textContent=game.icon||"🎮";$("#setupTitle").textContent=game.name.vi;$("#setupDescription").textContent=META[game.id]?.desc||"";
  const fields=$("#setupFields");fields.innerHTML="";
  if(game.topicSelectable)addSelect("topic","Chủ đề",State.bootstrap.topics.filter(t=>["animal","transport","plant","object","flag"].includes(t.id)).map(t=>[t.id,t.name.vi]));
  if(game.difficultySelectable)addSelect("difficulty","Cấp độ",[["easy","Dễ"],["normal","Vừa"],["hard","Khó"]]);
  const allocation=currentSessionGame(game.id);if(allocation){const p=document.createElement("p");p.className="instruction";p.textContent="Thời lượng của trò trong phiên: "+allocation.duration_minutes+" phút";fields.appendChild(p)}
  UI.modal.classList.add("show")
}
function addSelect(name,label,options){
  const l=document.createElement("label"),s=document.createElement("select");l.textContent=label;s.name=name;options.forEach(([v,t])=>s.add(new Option(t,v)));s.onchange=()=>State.setup[name]=s.value;State.setup[name]=s.value;l.appendChild(s);$("#setupFields").appendChild(l)
}
function startCurrentGame(){
  UI.modal.classList.remove("show");switchView("game");setScore(0);
  $("#gameTitle").textContent=State.current.name.vi;$("#gameMeta").textContent=["Dễ","Vừa","Khó"][["easy","normal","hard"].indexOf(State.setup.difficulty)]||"";
  const id=State.current.id;
  State.timerMinutes=currentSessionGame(State.current.id)?.duration_minutes||5;
  const delayedTimer=["image-answer","alphabet-en","alphabet-vi"].includes(id);
  if(delayedTimer){clearInterval(State.timer);State.timer=null;State.remaining=State.timerMinutes*60;$("#gameTime").textContent="CHUẨN BỊ"}else startTimer(State.timerMinutes);
  if(id==="listen-image-en")return quizGame("listen","en");
  if(id==="listen-image-vi")return quizGame("listen","vi");
  if(id==="image-answer")return quizGame("image","vi");
  if(id==="count")return countGame();
  if(id==="puzzle")return puzzleGame();
  if(id==="sudoku")return sudokuGame();
  if(id==="alphabet-en")return alphabetGame("en");
  if(id==="alphabet-vi")return alphabetGame("vi");
  if(id==="memory")return memoryGame();
  if(id==="bomber")return bomberGame();
  if(id==="hidden-object")return hiddenObjectGame();
  if(id==="tic-tac-toe")return ticTacToe();
  if(id==="colors")return colorGame();
  if(id==="space-shooter")return spaceShooter();
  if(id==="math-basic")return mathGame(false);
  if(id==="math-advanced")return mathGame(true);
  if(id==="match-transport")return matchGame("transport");
  if(id==="match-habitat")return matchGame("habitat");
}
function startTimer(minutes){
  clearInterval(State.timer);State.remaining=minutes*60;
  const draw=()=>{$("#gameTime").textContent=String(Math.floor(State.remaining/60)).padStart(2,"0")+":"+String(State.remaining%60).padStart(2,"0")};draw();
  State.timer=setInterval(()=>{State.remaining--;draw();if(State.remaining<=0){clearInterval(State.timer);finishGame(false,"Hết thời gian của trò chơi")}},1000)
}
function stopGame(){clearInterval(State.timer);State.timer=null;if(State.cleanup)try{State.cleanup()}catch{}State.cleanup=null;speechSynthesis.cancel();if(UI.stage)UI.stage.innerHTML=""}
function finishGame(won,title){
  clearInterval(State.timer);if(State.cleanup)try{State.cleanup()}catch{}State.cleanup=null;
  UI.stage.innerHTML='<div class="result-box"><div class="result-icon">'+(won?"🏆":"⏱️")+"</div><h2>"+escapeHtml(title)+"</h2><p class=\"instruction\">Bạn đạt "+State.score+' điểm trong lượt này.</p><div class="result-actions"><button id="againButton" class="primary-button">Chơi lại</button><button id="listButton" class="secondary-button">Danh sách trò</button></div></div>';
  $("#againButton").onclick=startCurrentGame;$("#listButton").onclick=()=>switchView("games")
}
async function topicData(id){
  if(!State.topicCache.has(id))State.topicCache.set(id,fetch("/api/topic/"+id).then(r=>{if(!r.ok)throw Error("Không tải được chủ đề");return r.json()}));
  return State.topicCache.get(id)
}
const validItems=d=>(d.items||[]).filter(x=>x.enabled!==false&&x.image&&x.viName&&x.enName);
async function getGameItems(n=12){const d=await topicData(State.setup.topic||"animal");return shuffle(validItems(d)).slice(0,n)}

async function quizGame(mode,language){
  const pool=await getGameItems(20),rounds=State.setup.difficulty==="hard"?12:State.setup.difficulty==="normal"?9:6;let round=0,timerStarted=mode!=="image";
  const next=async()=>{
    if(round>=rounds)return finishGame(true,"Hoàn thành thử thách!");
    const correct=pool[round%pool.length],choices=shuffle([correct,...shuffle(pool.filter(x=>x!==correct)).slice(0,3)]),name=language==="en"?correct.enName:correct.viName;
    UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">CÂU '+(round+1)+" / "+rounds+'</span><h2>'+(mode==="listen"?"Nghe và chọn hình":"Hình này tên là gì?")+'</h2>'+(mode==="listen"?'<button id="listenPrompt" class="primary-button">🔊 Nghe lại</button>':'<img class="main-picture" src="'+asset(correct.image)+'" alt="">')+'<div class="'+(mode==="listen"?"choice-grid":"answer-grid")+'">'+choices.map((x,i)=>'<button class="'+(mode==="listen"?"choice":"answer")+'" data-i="'+i+'">'+(mode==="listen"?'<img src="'+thumb(x.image)+'" alt=""><b>'+escapeHtml(language==="en"?x.enName:x.viName)+"</b>":escapeHtml(language==="en"?x.enName:x.viName))+"</button>").join("")+"</div></div>";
    if(mode==="listen"){const say=()=>speak(name,language==="en"?"en-US":"vi-VN");$("#listenPrompt").onclick=say;setTimeout(say,250)}
    if(mode==="image"){
      const buttons=$$("[data-i]");buttons.forEach(b=>b.disabled=true);
      for(let i=0;i<buttons.length;i++){buttons[i].classList.add("previewing");await speakAsync(choices[i].viName,"vi-VN");await new Promise(r=>setTimeout(r,180));buttons[i].classList.remove("previewing")}
      buttons.forEach(b=>b.disabled=false);if(!timerStarted){timerStarted=true;startTimer(State.timerMinutes);showToast("Bắt đầu tính giờ!")}
    }
    $$("[data-i]").forEach((b,i)=>b.onclick=()=>{if(choices[i]===correct){reward(20);round++;setTimeout(next,450)}else miss("Chưa đúng, hãy quan sát lại")})
  };next()
}
function countGame(){
  let round=0,total=State.setup.difficulty==="hard"?12:8;const icons=["🍎","⭐","🐟","🚗","🌼","🎈"];
  const next=()=>{if(round>=total)return finishGame(true,"Bé đếm rất giỏi!");const answer=2+Math.floor(Math.random()*(State.setup.difficulty==="hard"?15:8)),icon=icons[round%icons.length],answers=shuffle([answer,answer+1,Math.max(1,answer-1),answer+2]);
    UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">CÂU '+(round+1)+" / "+total+'</span><h2>Có bao nhiêu hình?</h2><div style="max-width:720px;margin:25px auto;font-size:52px;line-height:1.5">'+Array(answer).fill(icon).join(" ")+'</div><div class="answer-grid">'+answers.map(x=>'<button class="answer">'+x+"</button>").join("")+"</div></div>";
    $$(".answer").forEach((b,i)=>b.onclick=()=>{if(answers[i]===answer){reward(15);round++;next()}else miss()})
  };next()
}
async function puzzleGame(){
  const item=(await getGameItems(1))[0],size=State.setup.difficulty==="hard"?4:3,total=size*size;let order=shuffle([...Array(total).keys()]),selected=null;
  const draw=()=>{UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">GHÉP HÌNH</span><h2>'+escapeHtml(item.viName)+'</h2><img src="'+asset(item.image)+'" alt="" style="width:90px;height:70px;object-fit:contain"><p class="instruction">Chọn hai mảnh để đổi vị trí.</p><div id="puzzleBoard" style="--size:'+size+';display:grid;grid-template-columns:repeat('+size+',1fr);width:min(600px,90vw);aspect-ratio:1;margin:18px auto;gap:3px">'+order.map((piece,pos)=>'<button data-pos="'+pos+'" style="border:2px solid '+(selected===pos?"var(--yellow)":"transparent")+';background-image:url('+asset(item.image)+');background-size:'+size*100+"% "+size*100+"%;background-position:"+((piece%size)/(size-1)*100)+"% "+(Math.floor(piece/size)/(size-1)*100)+'%;border-radius:8px"></button>').join("")+"</div></div>";
    $$("[data-pos]").forEach(b=>b.onclick=()=>{const p=+b.dataset.pos;if(selected===null){selected=p;draw()}else{[order[selected],order[p]]=[order[p],order[selected]];selected=null;if(order.every((v,i)=>v===i)){reward(100);draw();const board=$("#puzzleBoard");board.classList.add("puzzle-complete");board.insertAdjacentHTML("afterend",'<div class="puzzle-celebration" aria-live="polite">✨ Chính xác! ✨</div>');$$("[data-pos]").forEach(x=>x.disabled=true);return setTimeout(()=>finishGame(true,"Ghép hình hoàn chỉnh!"),2000)}draw()}})
  };draw()
}
function sudokuGame(){
  const size=State.setup.difficulty==="hard"?6:4,boxR=size===6?2:2,boxC=size===6?3:2,solution=Array.from({length:size},(_,r)=>Array.from({length:size},(_,c)=>(r*boxC+Math.floor(r/boxR)+c)%size+1)),holes=size===6?18:8,board=solution.map(r=>[...r]);
  shuffle([...Array(size*size).keys()]).slice(0,holes).forEach(i=>board[Math.floor(i/size)][i%size]=0);
  UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">SUDOKU '+size+" × "+size+'</span><h2>Điền số còn thiếu</h2><div class="sudoku-grid" style="--size:'+size+'">'+board.flatMap((row,r)=>row.map((v,c)=>'<button class="sudoku-cell '+(v?"fixed":"")+'" data-r="'+r+'" data-c="'+c+'">'+(v||"")+"</button>")).join("")+'</div><button id="checkSudoku" class="primary-button">Kiểm tra</button></div>';
  $$(".sudoku-cell:not(.fixed)").forEach(b=>b.onclick=()=>{const r=+b.dataset.r,c=+b.dataset.c;board[r][c]=board[r][c]%size+1;b.textContent=board[r][c];b.classList.remove("wrong")});
  $("#checkSudoku").onclick=()=>{let ok=true;$$(".sudoku-cell:not(.fixed)").forEach(b=>{const r=+b.dataset.r,c=+b.dataset.c,wrong=board[r][c]!==solution[r][c];b.classList.toggle("wrong",wrong);ok&&=!wrong});if(ok){reward(120);finishGame(true,"Sudoku chính xác!")}else miss("Một vài ô chưa đúng")}
}
async function alphabetGame(lang){
  const letters=(lang==="en"?"ABCDEFGHIJKLMNOPQRSTUVWXYZ":"AĂÂBCDĐEÊGHIKLMNOÔƠPQRSTUƯVXY").split("");
  const viNames={A:"a",Ă:"á",Â:"ớ",B:"bê",C:"xê",D:"dê",Đ:"đê",E:"e",Ê:"ê",G:"giê",H:"hát",I:"i",K:"ca",L:"e lờ",M:"em mờ",N:"en nờ",O:"o",Ô:"ô",Ơ:"ơ",P:"pê",Q:"quy",R:"e rờ",S:"ét",T:"tê",U:"u",Ư:"ư",V:"vê",X:"ích xì",Y:"i dài"};
  const sayName=letter=>lang==="en"?letter:viNames[letter]||letter;
  UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">'+(lang==="en"?"ENGLISH ALPHABET":"BẢNG CHỮ CÁI TIẾNG VIỆT")+'</span><h2 id="alphabetGuide">Chạm vào chữ để nghe</h2><button id="readAlphabet" class="primary-button">🔊 Đọc toàn bộ bảng chữ cái</button><div class="alphabet-grid">'+letters.map(x=>'<button class="letter">'+x+"</button>").join("")+"</div></div>";
  const buttons=$$(".letter");
  buttons.forEach(b=>b.onclick=()=>{speak(sayName(b.textContent),lang==="en"?"en-US":"vi-VN");reward(2,"Đã nghe chữ "+b.textContent)});
  $("#readAlphabet").onclick=async()=>{const readButton=$("#readAlphabet");readButton.disabled=true;buttons.forEach(b=>b.disabled=true);for(let i=0;i<buttons.length;i++){buttons[i].classList.add("speaking");await speakAsync(sayName(letters[i]),lang==="en"?"en-US":"vi-VN");buttons[i].classList.remove("speaking")}buttons.forEach(b=>b.disabled=false);readButton.disabled=false};
  startTimer(State.timerMinutes)
}
async function memoryGame(){
  const count=State.setup.difficulty==="hard"?8:6,items=await getGameItems(count),cards=shuffle(items.flatMap((x,i)=>[{...x,key:i},{...x,key:i}]));let open=[],done=new Set;
  const draw=()=>{UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">TRÍ NHỚ HÌNH ẢNH</span><h2>Tìm các cặp giống nhau</h2><div class="memory-grid">'+cards.map((x,i)=>'<button class="memory-card '+(open.includes(i)?"open":"")+(done.has(x.key)?" done":"")+'" data-i="'+i+'">'+(open.includes(i)||done.has(x.key)?'<img src="'+thumb(x.image)+'" alt="'+escapeHtml(x.viName)+'">':"?")+"</button>").join("")+"</div></div>";
    $$(".memory-card:not(.done)").forEach(b=>b.onclick=()=>{const i=+b.dataset.i;if(open.includes(i)||open.length===2)return;open.push(i);draw();if(open.length===2)setTimeout(()=>{if(cards[open[0]].key===cards[open[1]].key){done.add(cards[open[0]].key);reward(20)}else miss("Hai hình chưa giống nhau");open=[];if(done.size===count)return finishGame(true,"Đã tìm đủ các cặp!");draw()},650)})
  };draw()
}
function bomberGame(){
  const size=State.setup.difficulty==="hard"?16:State.setup.difficulty==="normal"?12:9,mineCount=State.setup.difficulty==="hard"?45:State.setup.difficulty==="normal"?24:10,total=size*size;
  const mines=new Set(shuffle([...Array(total).keys()]).slice(0,mineCount)),open=new Set,flags=new Set;let ended=false;
  const neighbours=i=>{const r=Math.floor(i/size),c=i%size,out=[];for(let dr=-1;dr<=1;dr++)for(let dc=-1;dc<=1;dc++){const nr=r+dr,nc=c+dc;if((dr||dc)&&nr>=0&&nr<size&&nc>=0&&nc<size)out.push(nr*size+nc)}return out};
  const count=i=>neighbours(i).filter(n=>mines.has(n)).length;
  const reveal=i=>{if(open.has(i)||flags.has(i)||ended)return;if(mines.has(i)){ended=true;mines.forEach(x=>open.add(x));draw();setTimeout(()=>finishGame(false,"Bom đã phát nổ!"),500);return}const queue=[i];while(queue.length){const x=queue.shift();if(open.has(x)||flags.has(x)||mines.has(x))continue;open.add(x);if(count(x)===0)neighbours(x).forEach(n=>{if(!open.has(n))queue.push(n)})}if(open.size===total-mineCount){ended=true;reward(150,"Dò mìn hoàn tất");draw();setTimeout(()=>finishGame(true,"Đã phá hết bãi bom!"),450)}else draw()};
  const flag=i=>{if(open.has(i)||ended)return;flags.has(i)?flags.delete(i):flags.add(i);draw()};
  const draw=()=>{UI.stage.innerHTML='<div class="game-panel mines-panel"><span class="eyebrow">DÒ MÌN · PHÁ BOM</span><h2>Mở ô an toàn, đánh dấu vị trí có bom</h2><p class="instruction">💣 '+mineCount+' &nbsp; · &nbsp; 🚩 '+flags.size+'</p><div class="mines-grid" style="--mine-size:'+size+'">'+[...Array(total).keys()].map(i=>{const n=count(i),opened=open.has(i);return '<button class="mine-cell '+(opened?'open':'')+'" data-mine-cell="'+i+'">'+(opened?(mines.has(i)?'💣':n||''):flags.has(i)?'🚩':'')+'</button>'}).join('')+'</div><p class="instruction">Nhấp để mở · nhấp chuột phải để cắm cờ</p></div>';$$('[data-mine-cell]').forEach(b=>{const i=+b.dataset.mineCell;b.onclick=()=>reveal(i);b.oncontextmenu=e=>{e.preventDefault();flag(i)}})};draw()
}
async function hiddenObjectGame(){
  const topics=await Promise.all(["animal","transport","plant","object"].map(topicData)),transparent=x=>/transparent-library|transparent-v84/i.test(x.image||""),transparentPool=topics.flatMap(validItems).filter(transparent),library=shuffle(transparentPool.length?transparentPool:topics.flatMap(validItems)).slice(0,80),environments=validItems(await topicData("environment")),level=1+Math.floor(Math.random()*30),target=library[level%library.length],scene=environments[(level-1)%environments.length],required=State.setup.difficulty==="hard"?8:State.setup.difficulty==="normal"?6:4;
  const positions=shuffle([[5,10],[18,35],[32,8],[44,45],[58,17],[72,38],[84,9],[10,68],[29,64],[51,70],[68,63],[84,70]]).slice(0,required).map(([x,y],i)=>[x,y,34+(level*7+i*11)%35,-14+(level*5+i*9)%28]);
  UI.stage.innerHTML='<div class="game-panel hidden-panel"><div class="hidden-targets"><span>Màn '+level+'/30 · '+escapeHtml(scene.viName)+'</span><span><img src="'+asset(target.image)+'" alt="'+escapeHtml(target.viName)+'"> '+escapeHtml(target.viName)+' × <b id="hiddenRemaining">'+required+'</b></span></div><div class="hidden-scene themed-scene"><img class="hidden-scene-background" src="'+asset(scene.image)+'" alt="'+escapeHtml(scene.viName)+'">'+positions.map((p,i)=>'<button class="hidden-object" aria-label="'+escapeHtml(target.viName)+' ẩn số '+(i+1)+'" data-hidden="'+i+'" style="left:'+p[0]+'%;top:'+p[1]+'%;width:'+p[2]+'px;transform:rotate('+p[3]+'deg);opacity:'+(0.58+(i%3)*.13)+'"><img src="'+asset(target.image)+'" alt=""></button>').join('')+'</div></div>';
  let found=0;$$("[data-hidden]").forEach(b=>b.onclick=()=>{b.classList.add("found");reward(25,"Đã tìm thấy "+target.viName);$("#hiddenRemaining").textContent=required-(++found);if(found===required)setTimeout(()=>finishGame(true,"Đã tìm đủ "+required+" "+target.viName+"!"),500)})
}
function ticTacToe(){
  UI.stage.innerHTML='<div class="game-panel caro-panel"><span class="eyebrow">CARO VÔ HẠN · 5 QUÂN LIÊN TIẾP</span><h2 id="caroTurn">Lượt của người chơi X</h2><p class="instruction">Kéo bàn cờ để di chuyển · chạm một ô để đánh</p><canvas id="caroCanvas" class="caro-canvas"></canvas></div>';
  const cv=$("#caroCanvas"),ctx=cv.getContext("2d"),marks=new Map,cell=48;let player="X",offsetX=0,offsetY=0,drag=null,moved=false,running=true;
  const draw=()=>{if(!running)return;const w=cv.clientWidth,h=cv.clientHeight;ctx.clearRect(0,0,w,h);ctx.fillStyle="#071d2b";ctx.fillRect(0,0,w,h);ctx.strokeStyle="rgba(255,255,255,.16)";ctx.lineWidth=1;const sx=((offsetX%cell)+cell)%cell,sy=((offsetY%cell)+cell)%cell;for(let x=sx;x<w;x+=cell){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}for(let y=sy;y<h;y+=cell){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}ctx.textAlign="center";ctx.textBaseline="middle";ctx.font="700 31px Space Grotesk";for(const [k,v] of marks){const [x,y]=k.split(",").map(Number),px=offsetX+x*cell+cell/2,py=offsetY+y*cell+cell/2;if(px>-cell&&px<w+cell&&py>-cell&&py<h+cell){ctx.fillStyle=v==="X"?"#5de1db":"#ffd166";ctx.fillText(v,px,py)}}};
  const resize=()=>{const rect=cv.getBoundingClientRect(),dpr=devicePixelRatio||1;cv.width=Math.round(rect.width*dpr);cv.height=Math.round(rect.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw()},key=(x,y)=>x+","+y;
  const lineCount=(x,y,dx,dy,p)=>{let n=0;for(let s=1;marks.get(key(x+dx*s,y+dy*s))===p;s++)n++;return n};
  const place=(clientX,clientY)=>{const r=cv.getBoundingClientRect(),x=Math.floor((clientX-r.left-offsetX)/cell),y=Math.floor((clientY-r.top-offsetY)/cell),k=key(x,y);if(marks.has(k))return;marks.set(k,player);draw();const won=[[1,0],[0,1],[1,1],[1,-1]].some(([dx,dy])=>1+lineCount(x,y,dx,dy,player)+lineCount(x,y,-dx,-dy,player)>=5);if(won){running=false;reward(120);setTimeout(()=>finishGame(true,"Người chơi "+player+" chiến thắng!"),350);return}player=player==="X"?"O":"X";$("#caroTurn").textContent="Lượt của người chơi "+player};
  cv.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,ox:offsetX,oy:offsetY};moved=false;cv.setPointerCapture(e.pointerId)};cv.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.hypot(dx,dy)>5)moved=true;offsetX=drag.ox+dx;offsetY=drag.oy+dy;draw()};cv.onpointerup=e=>{if(!drag)return;if(!moved)place(e.clientX,e.clientY);drag=null};addEventListener("resize",resize);State.cleanup=()=>{running=false;removeEventListener("resize",resize)};resize()
}
function colorGame(){
  const base="images/topic-pack-v82/",colors=[["Đỏ","#e53935",base+"pack-v82-plant-apple.png"],["Cam","#fb8c00",base+"pack-v82-plant-orange.png"],["Vàng","#fdd835",base+"pack-v82-plant-banana.png"],["Xanh lá","#43a047",base+"pack-v82-plant-cactus.png"],["Xanh dương","#1e88e5",base+"pack-v82-transport-airplane.png"],["Tím","#8e24aa",base+"pack-v82-plant-grape.png"],["Hồng","#ec407a",base+"pack-v82-object-kite.png"],["Nâu","#795548",base+"pack-v82-object-guitar.png"],["Đen","#202124",base+"pack-v82-object-camera.png"],["Trắng","#f5f5f5",base+"pack-v82-object-piano.png"]];let target=colors[0],round=0;
  const card=c=>'<button class="color-card object-color-card" data-name="'+c[0]+'" style="--object-color:'+c[1]+'"><img src="'+asset(c[2])+'" alt=""><b>'+c[0]+'</b></button>',draw=()=>{if(round===8)return finishGame(true,"Đã thuộc các màu sắc!");target=colors[Math.floor(Math.random()*colors.length)];UI.stage.innerHTML='<div class="game-panel color-lab"><span class="eyebrow">PHÒNG THÍ NGHIỆM MÀU SẮC</span><h2>Vật nào có màu '+target[0]+'?</h2><div class="color-hero" style="--swatch:'+target[1]+'"><img src="'+asset(target[2])+'" alt=""><b>'+target[0]+'</b></div><button id="hearColor" class="primary-button">🔊 Nghe tên màu</button><div class="color-grid">'+shuffle(colors).map(card).join("")+"</div></div>";$("#hearColor").onclick=()=>speak(target[0]);$$(".color-card").forEach(b=>b.onclick=()=>{if(b.dataset.name===target[0]){b.classList.add("correct");reward(15);round++;setTimeout(draw,500)}else miss()})};draw()
}
function mathGame(advanced){
  let round=0,total=10;const next=()=>{if(round===total)return finishGame(true,"Hoàn thành bài toán!");const level={easy:0,normal:1,hard:2}[State.setup.difficulty],a=2+Math.floor(Math.random()*(8+level*12)),b=1+Math.floor(Math.random()*(8+level*6));let op,answer;if(advanced){op=round%2?"×":"÷";if(op==="×")answer=a*b;else{answer=a;a*=b}}else{op=round%2?"+":"−";answer=op==="+"?a+b:Math.max(a,b)-Math.min(a,b)}const q=op==="−"?Math.max(a,b)+" − "+Math.min(a,b):a+" "+op+" "+b,answers=shuffle([answer,answer+1,Math.max(0,answer-1),answer+2]);
    UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">CÂU '+(round+1)+" / "+total+'</span><h2 style="font-size:70px">'+q+' = ?</h2><button id="hearMath" class="primary-button">🔊 Nghe lại</button><div class="answer-grid">'+answers.map(x=>'<button class="answer">'+x+"</button>").join("")+"</div></div>";const read=async()=>{const buttons=$$(".answer");buttons.forEach(b=>b.disabled=true);await speakAsync("Câu hỏi: "+q+" bằng bao nhiêu?","vi-VN");for(let i=0;i<buttons.length;i++){buttons[i].classList.add("previewing");await speakAsync("Đáp án "+answers[i],"vi-VN");buttons[i].classList.remove("previewing")}buttons.forEach(b=>b.disabled=false)};$("#hearMath").onclick=read;$$(".answer").forEach((x,i)=>x.onclick=()=>{if(answers[i]===answer){reward(20);round++;next()}else miss()});read()};next()
}
async function matchGame(type){
  const isTransport=type==="transport",pool=validItems(await topicData(isTransport?"transport":"animal")).sort((a,b)=>Number(String(b.id||"").startsWith("pack-v82"))-Number(String(a.id||"").startsWith("pack-v82"))),used=new Set;
  const specs=isTransport?[
    {key:"road",find:/xe đạp|ô tô|xe hơi|xe buýt|mô tô|bicycle|car|bus|motor/i,image:"transport-mode-road-v83.png"},
    {key:"waterway",find:/ca nô|canoe|phà|ferry/i,image:"transport-mode-waterway-v83.png"},
    {key:"aviation",find:/máy bay|trực thăng|airplane|helicopter/i,image:"transport-mode-aviation-v83.png"},
    {key:"rail",find:/tàu hỏa|xe lửa|train|tram/i,image:"transport-mode-rail-v83.png"},
    {key:"maritime",find:/tàu thủy|tàu biển|thuyền buồm|ship|sailboat/i,image:"transport-mode-maritime-v83.png"},
    {key:"military",find:/xe quân sự|tàu quân sự|military/i,image:"transport-mode-military-v83.png"},
    {key:"road-heavy",find:/xe tải|máy kéo|truck|tractor/i,image:"transport-mode-road-v83.png"},
    {key:"space-flight",find:/tên lửa|rocket/i,image:"transport-mode-aviation-v83.png"}
  ]:[
    {key:"ocean",find:/rùa|turtle/i,image:"environment-ocean-v83.png"},
    {key:"farmland",find:/con bò|bò$|cow/i,image:"environment-farmland-v83.png"},
    {key:"forest",find:/sư tử|lion/i,image:"environment-forest-v83.png"},
    {key:"grassland",find:/thỏ|rabbit/i,image:"environment-grassland-v83.png"},
    {key:"snow",find:/gấu|bear/i,image:"environment-snow-mountain-v83.png"},
    {key:"river",find:/vịt|duck/i,image:"environment-river-v83.png"},
    {key:"countryside",find:/chó|dog/i,image:"environment-countryside-v83.png"},
    {key:"maple",find:/bướm|butterfly/i,image:"environment-maple-forest-v83.png"}
  ];
  const pairCount=State.setup.difficulty==="hard"?8:State.setup.difficulty==="normal"?6:4,activeSpecs=specs.slice(0,pairCount),entries=activeSpecs.map((s,i)=>{let item=pool.find((x,n)=>!used.has(n)&&s.find.test(x.viName+" "+x.enName)),idx=item?pool.indexOf(item):-1;if(!item){idx=pool.findIndex((x,n)=>!used.has(n));item=pool[idx]}used.add(idx);return {...s,item}}),left=shuffle(entries),right=shuffle(activeSpecs);let selected=null,done=0;
  UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">KÉO ẢNH ĐỂ NỐI</span><h2>'+(isTransport?'Đưa phương tiện vào đúng môi trường di chuyển':'Đưa con vật vào đúng môi trường sống')+'</h2><div class="visual-match-board" id="visualMatchBoard"><svg class="match-lines" id="matchLines"></svg><div class="match-column source-column">'+left.map((x,i)=>'<button class="visual-match-item" draggable="true" aria-label="'+escapeHtml(x.item.viName)+'" data-source="'+i+'"><img src="'+thumb(x.item.image)+'" alt=""></button>').join('')+'</div><div class="match-column target-column">'+right.map((x,i)=>'<button class="visual-match-target" aria-label="Môi trường số '+(i+1)+'" data-target-key="'+x.key+'"><img src="'+asset('images/transparent-library/'+x.image)+'" alt=""></button>').join('')+'</div></div><p class="instruction">Kéo ảnh bên trái và thả vào ảnh phù hợp bên phải</p></div>';
  const lines=[];
  const drawLines=()=>{const board=$("#visualMatchBoard"),svg=$("#matchLines");if(!board||!svg)return;const br=board.getBoundingClientRect();svg.setAttribute("viewBox","0 0 "+br.width+" "+br.height);svg.innerHTML=lines.map(x=>{const a=x.source.getBoundingClientRect(),b=x.target.getBoundingClientRect();return '<line x1="'+(a.right-br.left)+'" y1="'+(a.top+a.height/2-br.top)+'" x2="'+(b.left-br.left)+'" y2="'+(b.top+b.height/2-br.top)+'" />'}).join('')};
  const connect=(sourceIndex,target)=>{const source=$('[data-source="'+sourceIndex+'"]'),entry=left[sourceIndex];if(!source||source.classList.contains("done"))return;if(entry.key!==target.dataset.targetKey){target.classList.add("wrong");setTimeout(()=>target.classList.remove("wrong"),400);return miss("Hình này chưa đúng môi trường")};source.classList.add("done");target.classList.add("connected");lines.push({source,target});drawLines();reward(30,"Nối đúng!");selected=null;if(++done===entries.length)setTimeout(()=>finishGame(true,"Đã nối đúng tất cả hình ảnh!"),500)};
  $$("[data-source]").forEach(b=>{b.ondragstart=e=>{e.dataTransfer.setData("text/plain",b.dataset.source);e.dataTransfer.effectAllowed="move"};b.onclick=()=>{selected=+b.dataset.source;$$("[data-source]").forEach(x=>x.classList.toggle("selected",x===b))}});
  $$("[data-target-key]").forEach(b=>{b.ondragover=e=>{e.preventDefault();b.classList.add("dragover")};b.ondragleave=()=>b.classList.remove("dragover");b.ondrop=e=>{e.preventDefault();b.classList.remove("dragover");connect(+e.dataTransfer.getData("text/plain"),b)};b.onclick=()=>{if(selected!==null)connect(selected,b)}});addEventListener("resize",drawLines,{once:true})
}
function spaceShooter(){
  UI.stage.innerHTML='<div class="game-panel"><span class="eyebrow">METEOR DEFENDER · 3 TIM · 10 CẤP</span><h2>Phá hủy mục tiêu trước khi chúng xuyên thủng tuyến phòng thủ</h2><canvas id="spaceCanvas" class="space-canvas" width="900" height="540"></canvas><div class="controls"><button data-move="-1">←</button><button data-move="up">↑</button><span class="auto-fire-label">TỰ ĐỘNG BẮN · ĐỘ KHÓ TĂNG DẦN</span><button data-move="down">↓</button><button data-move="1">→</button></div></div>';
  const cv=$("#spaceCanvas"),ctx=cv.getContext("2d"),ship={x:450,y:490},shots=[],rocks=[],drops=[];let running=true,beams=1,angle=0,shipLevel=1,xp=0,hearts=3,ticks=0,invincible=0;
  const move=(dx,dy=0)=>{ship.x=Math.max(28,Math.min(872,ship.x+dx*36));ship.y=Math.max(290,Math.min(510,ship.y+dy*30))},fire=()=>{const n=Math.min(5,beams),maxAngle=Math.min(45,angle)*Math.PI/180;for(let i=0;i<n;i++){const a=n===1?0:-maxAngle/2+maxAngle*i/(n-1);shots.push({x:ship.x,y:ship.y-28,vx:Math.sin(a)*(10+shipLevel*.35),vy:-Math.cos(a)*(10+shipLevel*.35),power:1+Math.floor((shipLevel-1)/3)})}};
  $$("[data-move]").forEach(b=>b.onclick=()=>b.dataset.move==="up"?move(0,-1):b.dataset.move==="down"?move(0,1):move(+b.dataset.move));const key=e=>{if(e.key==="ArrowLeft"||e.key==="a")move(-1);if(e.key==="ArrowRight"||e.key==="d")move(1);if(e.key==="ArrowUp"||e.key==="w")move(0,-1);if(e.key==="ArrowDown"||e.key==="s")move(0,1)};addEventListener("keydown",key);
  cv.onpointermove=e=>{if(e.buttons||e.pointerType==="touch"){const r=cv.getBoundingClientRect();ship.x=Math.max(28,Math.min(872,(e.clientX-r.left)*900/r.width));ship.y=Math.max(290,Math.min(510,(e.clientY-r.top)*540/r.height))}};
  const collect=d=>{d.dead=true;if(d.type==="beam"){beams=Math.min(5,beams+1);reward(25,"Tăng lên "+beams+" tia đạn")}else if(d.type==="angle"){angle=Math.min(45,angle+9);reward(25,"Góc bắn "+angle+"°")}else{xp+=2;while(xp>=5&&shipLevel<10){xp-=5;shipLevel++;reward(50,"Phi thuyền lên cấp "+shipLevel)}}};
  const damage=message=>{if(invincible||!running)return;hearts--;invincible=75;miss(message+" · Còn "+hearts+" tim");if(hearts<=0)explode()},explode=()=>{running=false;for(let i=0;i<24;i++){ctx.fillStyle=i%2?"#ffcf5a":"#ff624d";ctx.beginPath();ctx.arc(ship.x+(Math.random()-.5)*130,ship.y+(Math.random()-.5)*100,7+Math.random()*22,0,Math.PI*2);ctx.fill()}setTimeout(()=>finishGame(false,"Phi thuyền đã nổ!"),650)};
  const drawMeteor=r=>{ctx.save();ctx.translate(r.x,r.y);ctx.rotate(r.spin);const g=ctx.createRadialGradient(-r.r*.28,-r.r*.32,2,0,0,r.r);g.addColorStop(0,["#d7a06f","#b78a67","#9f8d82","#8d6a62","#7c7087"][r.kind%5]);g.addColorStop(1,"#30252a");ctx.fillStyle=g;ctx.strokeStyle="#e4b17a88";ctx.lineWidth=2;ctx.beginPath();for(let i=0;i<12;i++){const a=i*Math.PI/6,rr=r.r*(.82+.18*Math.sin(i*4.7+r.seed));i?ctx.lineTo(Math.cos(a)*rr,Math.sin(a)*rr):ctx.moveTo(Math.cos(a)*rr,Math.sin(a)*rr)}ctx.closePath();ctx.fill();ctx.stroke();ctx.fillStyle="#241b2088";for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse((i-1)*r.r*.28,((i%2)-.5)*r.r*.38,r.r*(.10+i*.025),r.r*(.07+i*.02),i,0,Math.PI*2);ctx.fill()}ctx.restore()};
  const drawShip=()=>{ctx.save();ctx.translate(ship.x,ship.y);const s=1+shipLevel*.035;ctx.scale(s,s);ctx.globalAlpha=invincible&&ticks%8<4?.3:1;ctx.shadowColor=shipLevel>6?"#c594ff":"#52e9ff";ctx.shadowBlur=10+shipLevel*2;ctx.fillStyle=shipLevel>6?"#7a63d8":"#178ca7";ctx.strokeStyle="#e8fbff";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(0,-34-shipLevel);ctx.lineTo(19,-4);ctx.lineTo(14,23);ctx.lineTo(0,14);ctx.lineTo(-14,23);ctx.lineTo(-19,-4);ctx.closePath();ctx.fill();ctx.stroke();if(shipLevel>=3){ctx.fillStyle="#3559a8";for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(side*14,4);ctx.lineTo(side*(32+shipLevel),20);ctx.lineTo(side*13,17);ctx.closePath();ctx.fill()}}if(shipLevel>=6){ctx.fillStyle="#ffd166";ctx.fillRect(-30,10,7,18);ctx.fillRect(23,10,7,18)}if(shipLevel>=9){ctx.strokeStyle="#bda7ff";ctx.lineWidth=4;ctx.beginPath();ctx.arc(0,0,43,Math.PI*.15,Math.PI*.85,true);ctx.stroke()}ctx.fillStyle="#d8ffff";ctx.beginPath();ctx.ellipse(0,-7,6,10,0,0,Math.PI*2);ctx.fill();ctx.fillStyle="#ff8a45";ctx.beginPath();ctx.moveTo(-7,22);ctx.lineTo(0,39+Math.random()*8);ctx.lineTo(7,22);ctx.fill();ctx.restore()};
  const frame=()=>{if(!running)return;ticks++;invincible=Math.max(0,invincible-1);const wave=1+Math.floor(ticks/900),spawnEvery=Math.max(13,40-wave*2);if(ticks%Math.max(8,14-Math.floor(shipLevel/4))===0)fire();if(ticks%spawnEvery===0){const kind=Math.floor(Math.random()*10),r=13+kind*3.6,hp=Math.min(4,1+Math.floor(kind/3)+Math.floor(wave/5));rocks.push({x:30+Math.random()*840,y:-45,r,v:1.25+Math.random()*1.4+wave*.13,hp,maxHp:hp,kind,spin:0,seed:Math.random()*9})}shots.forEach(s=>{s.x+=s.vx;s.y+=s.vy});rocks.forEach(r=>{r.y+=r.v;r.spin+=.006+r.kind*.001});drops.forEach(d=>d.y+=2.2);
    for(const s of shots)for(const r of rocks)if(!s.dead&&!r.dead&&Math.hypot(s.x-r.x,s.y-r.y)<r.r+5){s.dead=true;r.hp-=s.power;if(r.hp<=0){r.dead=true;reward(10+5*r.maxHp,"Phá thiên thạch");xp++;while(xp>=5&&shipLevel<10){xp-=5;shipLevel++;showToast("Phi thuyền lên cấp "+shipLevel)}if(Math.random()<.3)drops.push({x:r.x,y:r.y,type:["beam","angle","level"][Math.floor(Math.random()*3)]})}}
    for(const d of drops)if(!d.dead&&Math.hypot(d.x-ship.x,d.y-ship.y)<38)collect(d);for(const r of rocks)if(!r.dead&&Math.hypot(r.x-ship.x,r.y-ship.y)<r.r+24){r.dead=true;damage("Va chạm thiên thạch")};for(const r of rocks)if(!r.dead&&r.y-r.r>540){r.dead=true;damage("Mục tiêu lọt qua phòng tuyến")}
    shots.splice(0,shots.length,...shots.filter(s=>!s.dead&&s.y>-30&&s.x>-20&&s.x<920));rocks.splice(0,rocks.length,...rocks.filter(r=>!r.dead));drops.splice(0,drops.length,...drops.filter(d=>!d.dead&&d.y<570));ctx.clearRect(0,0,900,540);ctx.fillStyle="#020914";ctx.fillRect(0,0,900,540);ctx.fillStyle="rgba(93,225,219,.035)";ctx.fillRect(0,270,900,270);ctx.fillStyle="#fff";for(let i=0;i<80;i++)ctx.fillRect((i*83)%900,(i*47+ticks*.15)%540,1.5,1.5);drawShip();shots.forEach(s=>{const g=ctx.createLinearGradient(s.x,s.y,s.x,s.y+20);g.addColorStop(0,shipLevel>6?"#fff":"#5de1db");g.addColorStop(1,shipLevel>3?"#9b8cff":"#168ca5");ctx.fillStyle=g;ctx.shadowColor=shipLevel>5?"#bf93ff":"#4ef6ff";ctx.shadowBlur=8+shipLevel;ctx.fillRect(s.x-2-shipLevel/5,s.y,4+shipLevel/2,20);ctx.shadowBlur=0});rocks.forEach(drawMeteor);drops.forEach(d=>{ctx.save();ctx.translate(d.x,d.y);ctx.fillStyle=d.type==="beam"?"#55e9ff":d.type==="angle"?"#ffd166":"#b98cff";ctx.rotate(ticks*.03);ctx.beginPath();for(let i=0;i<8;i++){const a=i*Math.PI/4,rr=i%2?8:17;ctx.lineTo(Math.cos(a)*rr,Math.sin(a)*rr)}ctx.closePath();ctx.fill();ctx.restore()});ctx.fillStyle="#fff";ctx.font="bold 15px sans-serif";ctx.textAlign="left";ctx.fillText("TIM "+hearts+"  ·  TIA "+beams+"  ·  GÓC "+angle+"°  ·  CẤP "+shipLevel+"/10  ·  ĐỘ KHÓ "+wave,20,28);requestAnimationFrame(frame)};State.cleanup=()=>{running=false;removeEventListener("keydown",key)};frame()
}

function renderTopics(){
  UI.topics.innerHTML="";State.bootstrap.topics.forEach((t,i)=>{const b=document.createElement("button");b.className="topic-button"+(i===0?" active":"");b.dataset.topic=t.id;b.innerHTML=(TOPIC_ICONS[t.id]||"✦")+" "+escapeHtml(t.name.vi);b.onclick=()=>loadTopic(t.id);UI.topics.appendChild(b)})
}
async function loadTopic(id){
  State.topic=id;State.visible=30;$$(".topic-button").forEach(b=>b.classList.toggle("active",b.dataset.topic===id));UI.libraryGrid.innerHTML='<div class="result-box">Đang mở thư viện…</div>';
  try{State.items=validItems(await topicData(id));renderLibrary()}catch(error){UI.libraryGrid.innerHTML='<div class="result-box"><h2>Chưa tải được thư viện</h2><p>'+escapeHtml(error.message)+"</p></div>"}
}
function filteredItems(){const q=(UI.search.value||"").toLocaleLowerCase("vi").trim();return q?State.items.filter(x=>(x.viName+" "+x.enName+" "+(x.description||"")).toLocaleLowerCase("vi").includes(q)):State.items}
function renderLibrary(){
  const items=filteredItems(),topic=State.bootstrap.topics.find(t=>t.id===State.topic);$("#librarySummary").textContent=items.length+" mục trong "+(topic?.name.vi||"thư viện");UI.libraryGrid.innerHTML="";
  items.slice(0,State.visible).forEach((x,i)=>{const b=document.createElement("button");b.className="library-card";b.innerHTML='<span class="library-card-image"><img loading="'+(i<10?"eager":"lazy")+'" src="'+thumb(x.image)+'" alt="'+escapeHtml(x.viName)+'"></span><span class="library-card-copy"><small>'+escapeHtml((topic?.name.vi||"THƯ VIỆN").toUpperCase())+"</small><b>"+escapeHtml(x.viName)+"</b><em>"+escapeHtml(x.enName)+"</em></span>";b.querySelector("img").onerror=e=>{e.currentTarget.src=asset(x.image)};b.onclick=()=>openDetail(x);UI.libraryGrid.appendChild(b)});
  $("#loadMore").hidden=State.visible>=items.length
}
function openDetail(item){
  State.detailItem=item;const topic=State.bootstrap.topics.find(t=>t.id===State.topic);$("#detailImage").src=asset(item.image);$("#detailImage").alt=item.viName;$("#detailTopic").textContent=(TOPIC_ICONS[State.topic]||"✦")+" "+(topic?.name.vi||"Thư viện");$("#detailName").textContent=item.viName;$("#detailEnglish").textContent=item.enName+" 🔊";$("#detailDescription").textContent=item.description||("Tên tiếng Anh là “"+item.enName+"”. Chạm nút nghe để luyện phát âm và ghi nhớ.");const facts=item.facts||[];$("#detailFacts").innerHTML=(facts.length?facts:[{label:"Tiếng Việt",value:item.viName},{label:"English",value:item.enName}]).slice(0,6).map(f=>"<span><b>"+escapeHtml(f.label||"Thông tin")+"</b><br>"+escapeHtml(f.value||f.text||"")+"</span>").join("");UI.detail.classList.add("show")
}
function renderDesign(){$("#designGrid").innerHTML=DESIGN.map(x=>'<article class="design-card"><span>'+x[0]+"</span><h3>"+x[1]+"</h3><p>"+x[2]+"</p></article>").join("")}

init();
