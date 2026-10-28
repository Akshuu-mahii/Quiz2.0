/* SmartQuiz Analytics AI - Frontend */
const API = window.location.origin + '/api';
let state = { user: null, token: localStorage.getItem('sq_token'), page: 'landing', quiz: null, attempt: null, answers: {}, marked: {}, currentQ: 0, timer: null, timeLeft: 0, charts: {}, result: null, selectedQuizId: null };

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401) { logout(); throw new Error('Unauthorized'); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : (data.detail?.[0]?.msg || 'Request failed'));
  return data;
}
function $(s) { return document.querySelector(s); }
function formatTime(s) { const m = Math.floor(s/60), sec = s%60; return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; }
function logout() { state.token=null; state.user=null; localStorage.removeItem('sq_token'); navigate('landing'); }
function navigate(page, data={}) { state.page=page; Object.assign(state,data); render(); window.scrollTo(0,0); }

function render() {
  const app = $('#app'); if (!app) return;
  Object.values(state.charts).forEach(c => c?.destroy?.()); state.charts = {};
  const pages = { landing: renderLanding, login: ()=>renderAuth('login'), register: ()=>renderAuth('register'), 'student-dash': renderStudentDash, quizzes: renderQuizzes, quiz: renderQuiz, result: renderResult, analytics: renderAnalytics, history: renderHistory, 'teacher-dash': renderTeacherDash, 'create-quiz': renderCreateQuiz, 'quiz-results': renderTeacherResults };
  app.innerHTML = (pages[state.page] || renderLanding)();
  bindEvents();
  if (state.page==='student-dash') loadStudentDash();
  if (state.page==='quizzes') loadQuizzes();
  if (state.page==='analytics') loadAnalytics();
  if (state.page==='history') loadHistory();
  if (state.page==='teacher-dash') loadTeacherDash();
  if (state.page==='quiz-results') loadTeacherResults();
  if (state.page==='landing') loadStats();
  if (state.page==='create-quiz') { loadSubjectsForCreate(); if (!$('#questions-container')?.children.length) addQuestion(); }
}

function navbar(active) {
  const isT = state.user?.role==='teacher';
  return `<nav class="glass sticky top-0 z-50 border-b border-white/5"><div class="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
  <div class="flex items-center gap-2 cursor-pointer" onclick="navigate('${isT?'teacher-dash':'student-dash'}')"><div class="w-9 h-9 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center"><i class="fas fa-brain text-white text-sm"></i></div><span class="font-bold text-lg gradient-text hidden sm:inline">SmartQuiz Analytics AI</span></div>
  <div class="flex items-center gap-1 sm:gap-3 text-sm">
  ${isT?`<button class="nav-link px-3 py-1 ${active==='teacher-dash'?'active':''}" onclick="navigate('teacher-dash')">Dashboard</button><button class="nav-link px-3 py-1 ${active==='create-quiz'?'active':''}" onclick="navigate('create-quiz')">Create Quiz</button>`
  :`<button class="nav-link px-3 py-1 ${active==='student-dash'?'active':''}" onclick="navigate('student-dash')">Dashboard</button><button class="nav-link px-3 py-1 ${active==='quizzes'?'active':''}" onclick="navigate('quizzes')">Quizzes</button><button class="nav-link px-3 py-1 ${active==='analytics'?'active':''}" onclick="navigate('analytics')">Analytics</button><button class="nav-link px-3 py-1 ${active==='history'?'active':''}" onclick="navigate('history')">History</button>`}
  <div class="flex items-center gap-2 ml-2 pl-3 border-l border-white/10"><span class="text-slate-400 hidden sm:inline">${state.user?.name||''}</span><button onclick="logout()" class="text-slate-400 hover:text-red-400"><i class="fas fa-sign-out-alt"></i></button></div>
  </div></div></nav>`;
}

function renderLanding() {
  return `<div class="min-h-screen">
  <nav class="glass sticky top-0 z-50 border-b border-white/5"><div class="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
  <div class="flex items-center gap-2"><div class="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-400 flex items-center justify-center shadow-glow"><i class="fas fa-brain text-white"></i></div><span class="font-bold text-xl gradient-text">SmartQuiz Analytics AI</span></div>
  <div class="flex gap-3"><button onclick="navigate('login')" class="btn-outline px-4 py-2 rounded-lg text-sm font-medium">Login</button><button onclick="navigate('register')" class="btn-primary px-4 py-2 rounded-lg text-sm font-medium text-white">Get Started</button></div>
  </div></nav>
  <section class="relative overflow-hidden"><div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-900/20 via-transparent to-transparent"></div>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 pt-20 pb-24 text-center relative">
  <h1 class="text-4xl sm:text-5xl md:text-6xl font-extrabold leading-tight mb-6">Test Your Knowledge.<br><span class="gradient-text">Analyze Your Performance.</span><br>Improve Every Day.</h1>
  <p class="text-slate-400 text-lg max-w-2xl mx-auto mb-10">Online quizzes powered by intelligent student performance analytics. Instant results, topic-level insights, and personalized recommendations.</p>
  <div class="flex flex-wrap justify-center gap-4">
  <button onclick="navigate('register')" class="btn-primary px-8 py-3.5 rounded-xl text-white font-semibold shadow-glow"><i class="fas fa-rocket mr-2"></i>Get Started Free</button>
  <button onclick="navigate('login')" class="btn-outline px-6 py-3.5 rounded-xl font-medium"><i class="fas fa-user-graduate mr-2"></i>Student Login</button>
  <button onclick="navigate('login')" class="btn-outline px-6 py-3.5 rounded-xl font-medium"><i class="fas fa-chalkboard-teacher mr-2"></i>Teacher Login</button>
  </div></div></section>
  <section class="max-w-7xl mx-auto px-4 sm:px-6 py-16"><h2 class="text-2xl font-bold text-center mb-10">Why SmartQuiz?</h2>
  <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
  ${[{i:'fa-clipboard-list',t:'Online Assessments',d:'MCQ quizzes with timers, navigation and mark-for-review.'},{i:'fa-bolt',t:'Instant Results',d:'Automatic evaluation with detailed score breakdown.'},{i:'fa-chart-line',t:'Performance Analytics',d:'Subject & topic insights, progress trends.'},{i:'fa-lightbulb',t:'Personalized Learning',d:'Recommendations based on real performance data.'}].map(f=>`<div class="glass glass-hover rounded-2xl p-6 transition"><div class="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center mb-4"><i class="fas ${f.i} text-purple-400 text-xl"></i></div><h3 class="font-semibold text-lg mb-2">${f.t}</h3><p class="text-slate-400 text-sm">${f.d}</p></div>`).join('')}
  </div></section>
  <section class="max-w-7xl mx-auto px-4 sm:px-6 py-12"><div class="glass rounded-2xl p-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center" id="platform-stats">
  <div><div class="text-3xl font-bold gradient-text" id="stat-quizzes">—</div><div class="text-slate-400 text-sm mt-1">Published Quizzes</div></div>
  <div><div class="text-3xl font-bold gradient-text" id="stat-students">—</div><div class="text-slate-400 text-sm mt-1">Students</div></div>
  <div><div class="text-3xl font-bold gradient-text" id="stat-attempts">—</div><div class="text-slate-400 text-sm mt-1">Assessments Completed</div></div>
  <div><div class="text-3xl font-bold gradient-text" id="stat-teachers">—</div><div class="text-slate-400 text-sm mt-1">Teachers</div></div>
  </div></section>
  <footer class="border-t border-white/5 mt-16 py-12"><div class="max-w-7xl mx-auto px-4 sm:px-6 grid sm:grid-cols-3 gap-8 text-sm text-slate-400">
  <div><div class="font-semibold text-white mb-3">About</div><p>Premium educational platform combining online assessments with deep performance analytics.</p></div>
  <div><div class="font-semibold text-white mb-3">Contact</div><p>support@smartquiz.ai</p></div>
  <div><div class="font-semibold text-white mb-3">Demo Accounts</div><p>Student: student@smartquiz.ai / student123</p><p>Teacher: teacher@smartquiz.ai / teacher123</p></div>
  </div><div class="text-center text-slate-600 text-xs mt-8">© 2026 SmartQuiz Analytics AI</div></footer></div>`;
}

async function loadStats() { try { const s=await api('/stats'); $('#stat-quizzes').textContent=s.total_quizzes; $('#stat-students').textContent=s.total_students; $('#stat-attempts').textContent=s.total_attempts; $('#stat-teachers').textContent=s.total_teachers; } catch(e){} }

function renderAuth(mode) {
  const isL=mode==='login';
  return `<div class="min-h-screen flex items-center justify-center px-4"><div class="glass rounded-2xl p-8 w-full max-w-md shadow-glass fade-in">
  <div class="text-center mb-8"><div class="w-14 h-14 mx-auto rounded-xl bg-gradient-to-br from-purple-500 to-cyan-400 flex items-center justify-center mb-4"><i class="fas fa-brain text-white text-xl"></i></div>
  <h1 class="text-2xl font-bold">${isL?'Welcome Back':'Create Account'}</h1><p class="text-slate-400 text-sm mt-1">${isL?'Sign in to continue':'Join SmartQuiz Analytics AI'}</p></div>
  <form id="auth-form" class="space-y-4">
  ${!isL?`<div><label class="text-sm text-slate-400">Full Name</label><input name="name" required class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5 focus:outline-none focus:border-purple-500" /></div>
  <div><label class="text-sm text-slate-400">Role</label><select name="role" class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5"><option value="student">Student</option><option value="teacher">Teacher</option></select></div>`:''}
  <div><label class="text-sm text-slate-400">Email</label><input name="email" type="email" required class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5 focus:outline-none focus:border-purple-500" /></div>
  <div><label class="text-sm text-slate-400">Password</label><input name="password" type="password" required minlength="6" class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5 focus:outline-none focus:border-purple-500" /></div>
  <div id="auth-error" class="text-red-400 text-sm hidden"></div>
  <button type="submit" class="btn-primary w-full py-3 rounded-xl text-white font-semibold">${isL?'Sign In':'Create Account'}</button>
  </form>
  <p class="text-center text-sm text-slate-400 mt-6">${isL?`Don't have an account? <button onclick="navigate('register')" class="text-purple-400 hover:underline">Register</button>`:`Already have an account? <button onclick="navigate('login')" class="text-purple-400 hover:underline">Login</button>`}</p>
  <button onclick="navigate('landing')" class="text-slate-500 text-sm mt-4 w-full text-center hover:text-slate-300">← Back to home</button>
  </div></div>`;
}

function renderStudentDash() {
  return `${navbar('student-dash')}<div class="max-w-7xl mx-auto px-4 sm:px-6 py-8 fade-in">
  <h1 class="text-2xl font-bold mb-1" id="welcome-msg">Welcome back!</h1><p class="text-slate-400 mb-8">Here's your learning overview</p>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8" id="kpi-cards">
  ${['Total Quizzes','Average Score','Highest Score','Accuracy'].map((l,i)=>`<div class="glass rounded-xl p-5"><div class="text-slate-400 text-xs uppercase tracking-wide">${l}</div><div class="text-2xl font-bold mt-1" id="kpi-${i}">—</div></div>`).join('')}
  </div>
  <div class="grid lg:grid-cols-3 gap-6">
  <div class="lg:col-span-2 space-y-6"><div class="glass rounded-xl p-6"><h2 class="font-semibold mb-4">Performance Trend</h2><canvas id="trend-chart" height="120"></canvas></div>
  <div class="glass rounded-xl p-6"><h2 class="font-semibold mb-4">Recent Quiz History</h2><div id="recent-list" class="space-y-3 text-sm">Loading...</div></div></div>
  <div class="space-y-6"><div class="glass rounded-xl p-6"><h2 class="font-semibold mb-4"><i class="fas fa-lightbulb text-yellow-400 mr-2"></i>Recommendations</h2><ul id="recs-list" class="space-y-2 text-sm text-slate-300"></ul></div>
  <div class="glass rounded-xl p-6"><h2 class="font-semibold mb-4">Available Quizzes</h2><div id="avail-list" class="space-y-3"></div><button onclick="navigate('quizzes')" class="text-purple-400 text-sm mt-3 hover:underline">View all →</button></div></div>
  </div></div>`;
}

async function loadStudentDash() {
  try {
    const d = await api('/student/dashboard');
    $('#welcome-msg').textContent = d.welcome;
    const s = d.stats;
    $('#kpi-0').textContent = s.total_attempts; $('#kpi-1').textContent = s.average_score+'%'; $('#kpi-2').textContent = s.highest_score+'%'; $('#kpi-3').textContent = s.overall_accuracy+'%';
    $('#recs-list').innerHTML = d.recommendations.map(r=>`<li class="flex gap-2"><span class="text-cyan-400">•</span>${r}</li>`).join('') || '<li class="text-slate-500">Take quizzes to get recommendations</li>';
    const recent = $('#recent-list');
    if (!d.recent_attempts.length) recent.innerHTML = '<p class="text-slate-500">No attempts yet.</p>';
    else recent.innerHTML = d.recent_attempts.map(a=>`<div class="flex justify-between items-center py-2 border-b border-white/5"><div><div class="font-medium">${a.quiz}</div><div class="text-slate-500 text-xs">${a.subject}</div></div><div class="font-semibold ${a.percentage>=70?'text-green-400':a.percentage>=50?'text-yellow-400':'text-red-400'}">${a.percentage}%</div></div>`).join('');
    $('#avail-list').innerHTML = d.available_quizzes.slice(0,4).map(q=>`<div class="flex justify-between items-center"><div><div class="font-medium text-sm">${q.title}</div><div class="text-xs text-slate-500">${q.subject?.name||''} · ${q.difficulty}</div></div><button onclick="startQuiz(${q.id})" class="text-xs btn-primary px-3 py-1.5 rounded-lg text-white">Start</button></div>`).join('') || '<p class="text-slate-500 text-sm">None</p>';
    const ctx = document.getElementById('trend-chart');
    if (ctx && d.progress_trend.length) {
      state.charts.trend = new Chart(ctx, { type:'line', data:{ labels:d.progress_trend.map(p=>p.quiz?.slice(0,12)||''), datasets:[{label:'Score %',data:d.progress_trend.map(p=>p.percentage),borderColor:'#a855f7',backgroundColor:'rgba(168,85,247,0.1)',fill:true,tension:0.3,pointBackgroundColor:'#22d3ee'}] }, options:{ responsive:true, plugins:{legend:{display:false}}, scales:{ x:{ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,0.04)'}}, y:{min:0,max:100,ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,0.04)'}} } } });
    }
  } catch(e){ console.error(e); }
}

function renderQuizzes() {
  return `${navbar('quizzes')}<div class="max-w-7xl mx-auto px-4 sm:px-6 py-8 fade-in"><h1 class="text-2xl font-bold mb-6">Available Quizzes</h1>
  <div class="flex flex-wrap gap-3 mb-6"><input id="quiz-search" placeholder="Search..." class="bg-dark-800 border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 w-48" />
  <select id="quiz-diff" class="bg-dark-800 border border-white/10 rounded-lg px-3 py-2 text-sm"><option value="">All Difficulties</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select>
  <button onclick="loadQuizzes()" class="btn-outline px-4 py-2 rounded-lg text-sm">Filter</button></div>
  <div id="quiz-grid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">Loading...</div></div>`;
}

async function loadQuizzes() {
  const search = $('#quiz-search')?.value||'', diff=$('#quiz-diff')?.value||'';
  let url='/quizzes?'; if(search) url+=`search=${encodeURIComponent(search)}&`; if(diff) url+=`difficulty=${diff}`;
  try {
    const quizzes = await api(url); const grid=$('#quiz-grid');
    if(!quizzes.length){ grid.innerHTML='<p class="text-slate-500 col-span-full">No quizzes found.</p>'; return; }
    grid.innerHTML = quizzes.map(q=>`<div class="glass glass-hover rounded-xl p-5 transition flex flex-col"><div class="flex items-start justify-between mb-3"><span class="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">${q.difficulty}</span><span class="text-xs text-slate-500">${q.duration_minutes} min</span></div>
    <h3 class="font-semibold mb-1">${q.title}</h3><p class="text-slate-400 text-sm mb-3 flex-1">${q.description||''}</p>
    <div class="flex items-center justify-between text-xs text-slate-500 mb-4"><span><i class="fas fa-book mr-1"></i>${q.subject?.name||'General'}</span><span>${q.question_count||'?'} Qs · ${q.total_marks} marks</span></div>
    <button onclick="startQuiz(${q.id})" class="btn-primary w-full py-2.5 rounded-lg text-white text-sm font-medium"><i class="fas fa-play mr-1"></i> Start Quiz</button></div>`).join('');
  } catch(e){ $('#quiz-grid').innerHTML=`<p class="text-red-400">${e.message}</p>`; }
}

async function startQuiz(quizId) {
  try {
    const attempt = await api('/attempts/start',{method:'POST',body:JSON.stringify({quiz_id:quizId})});
    const quiz = await api(`/quizzes/${quizId}`);
    state.quiz=quiz; state.attempt=attempt; state.answers={}; state.marked={}; state.currentQ=0; state.timeLeft=quiz.duration_minutes*60;
    navigate('quiz'); startTimer();
  } catch(e){ alert(e.message); }
}

function renderQuiz() {
  if(!state.quiz) return '<p>Loading...</p>';
  const q=state.quiz.questions[state.currentQ]; const total=state.quiz.questions.length; const answered=Object.keys(state.answers).length;
  return `<div class="min-h-screen bg-dark-950"><div class="glass sticky top-0 z-50 border-b border-white/5 px-4 py-3"><div class="max-w-5xl mx-auto flex items-center justify-between">
  <div><div class="font-semibold">${state.quiz.title}</div><div class="text-xs text-slate-400">${state.quiz.subject?.name} · ${state.quiz.difficulty}</div></div>
  <div class="flex items-center gap-4"><div class="text-sm"><span class="text-slate-400">Progress:</span> <span class="font-medium">${answered}/${total}</span></div>
  <div id="timer" class="font-mono text-lg font-bold ${state.timeLeft<60?'text-red-400 animate-pulse':'text-cyan-400'}">${formatTime(state.timeLeft)}</div></div></div></div>
  <div class="max-w-5xl mx-auto px-4 py-6 grid lg:grid-cols-4 gap-6">
  <div class="lg:col-span-3"><div class="glass rounded-xl p-6 mb-4"><div class="flex justify-between text-sm text-slate-400 mb-4"><span>Question ${state.currentQ+1} of ${total}</span><span>${q.marks} mark(s)</span></div>
  <h2 class="text-lg font-medium mb-6">${q.text}</h2><div class="space-y-3">${q.options.map(o=>`<div class="option-card border border-white/10 rounded-xl p-4 cursor-pointer transition hover:border-purple-500/50 ${state.answers[q.id]===o.id?'selected':''}" onclick="selectAnswer(${q.id},${o.id})">
  <div class="flex items-center gap-3"><div class="w-6 h-6 rounded-full border-2 ${state.answers[q.id]===o.id?'border-purple-500 bg-purple-500':'border-slate-600'} flex items-center justify-center">${state.answers[q.id]===o.id?'<i class="fas fa-check text-xs text-white"></i>':''}</div><span>${o.text}</span></div></div>`).join('')}</div></div>
  <div class="flex justify-between items-center"><button onclick="prevQ()" class="btn-outline px-5 py-2.5 rounded-lg text-sm ${state.currentQ===0?'opacity-40 pointer-events-none':''}"><i class="fas fa-arrow-left mr-1"></i> Previous</button>
  <button onclick="toggleMark(${q.id})" class="text-sm px-4 py-2 rounded-lg ${state.marked[q.id]?'bg-yellow-500/20 text-yellow-400':'text-slate-400 hover:text-yellow-400'}"><i class="fas fa-flag mr-1"></i> ${state.marked[q.id]?'Marked':'Mark for review'}</button>
  ${state.currentQ<total-1?`<button onclick="nextQ()" class="btn-primary px-5 py-2.5 rounded-lg text-sm text-white">Next <i class="fas fa-arrow-right ml-1"></i></button>`:`<button onclick="confirmSubmit()" class="btn-primary px-5 py-2.5 rounded-lg text-sm text-white" style="background:linear-gradient(135deg,#16a34a,#059669)">Submit Quiz</button>`}
  </div></div>
  <div class="glass rounded-xl p-4 h-fit sticky top-24"><div class="text-sm font-medium mb-3">Question Navigator</div>
  <div class="grid grid-cols-5 gap-2 mb-4">${state.quiz.questions.map((qq,i)=>{ let cls='bg-dark-700'; if(state.answers[qq.id]) cls='bg-purple-600'; if(state.marked[qq.id]) cls='bg-yellow-600'; if(i===state.currentQ) cls+=' ring-2 ring-cyan-400'; return `<button onclick="goToQ(${i})" class="w-9 h-9 rounded-lg text-xs font-medium ${cls}">${i+1}</button>`; }).join('')}</div>
  <div class="text-xs text-slate-400 space-y-1"><div class="flex items-center gap-2"><span class="w-3 h-3 rounded bg-purple-600"></span> Answered</div><div class="flex items-center gap-2"><span class="w-3 h-3 rounded bg-yellow-600"></span> Marked</div><div class="flex items-center gap-2"><span class="w-3 h-3 rounded bg-dark-700"></span> Unanswered</div></div>
  <button onclick="confirmSubmit()" class="btn-primary w-full mt-4 py-2.5 rounded-lg text-white text-sm">Submit Quiz</button></div>
  </div></div>`;
}

function selectAnswer(qid,oid){ state.answers[qid]=oid; render(); }
function toggleMark(qid){ state.marked[qid]=!state.marked[qid]; render(); }
function goToQ(i){ state.currentQ=i; render(); }
function prevQ(){ if(state.currentQ>0){ state.currentQ--; render(); } }
function nextQ(){ if(state.currentQ<state.quiz.questions.length-1){ state.currentQ++; render(); } }
function startTimer(){ clearInterval(state.timer); state.timer=setInterval(()=>{ state.timeLeft--; const t=$('#timer'); if(t){ t.textContent=formatTime(state.timeLeft); if(state.timeLeft<60) t.classList.add('text-red-400','animate-pulse'); } if(state.timeLeft<=0){ clearInterval(state.timer); submitQuiz(true); } },1000); }
function confirmSubmit(){ const u=state.quiz.questions.filter(q=>!state.answers[q.id]).length; if(confirm(u>0?`You have ${u} unanswered. Submit anyway?`:'Submit quiz?')) submitQuiz(); }
async function submitQuiz(){ clearInterval(state.timer); const responses=state.quiz.questions.map(q=>({question_id:q.id,selected_option_id:state.answers[q.id]||null,time_spent_seconds:0,marked_for_review:!!state.marked[q.id]})); try{ state.result=await api(`/attempts/${state.attempt.id}/submit`,{method:'POST',body:JSON.stringify({responses})}); navigate('result'); }catch(e){ alert(e.message); } }
window.addEventListener('beforeunload',e=>{ if(state.page==='quiz'&&state.attempt){ e.preventDefault(); e.returnValue=''; } });

function renderResult() {
  const r=state.result; if(!r) return '<p>No result</p>'; const pct=r.percentage;
  return `${navbar('')}<div class="max-w-3xl mx-auto px-4 py-10 fade-in"><div class="glass rounded-2xl p-8 text-center shadow-glow">
  <div class="text-sm text-slate-400 mb-2">Quiz Completed</div><h1 class="text-2xl font-bold mb-6">Your Results</h1>
  <div class="relative w-40 h-40 mx-auto mb-6"><svg class="w-full h-full -rotate-90" viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" fill="none" stroke="#1a1a24" stroke-width="8"/><circle cx="50" cy="50" r="42" fill="none" stroke="url(#grad)" stroke-width="8" stroke-dasharray="${2*Math.PI*42}" stroke-dashoffset="${2*Math.PI*42*(1-pct/100)}" stroke-linecap="round"/><defs><linearGradient id="grad"><stop offset="0%" stop-color="#a855f7"/><stop offset="100%" stop-color="#22d3ee"/></linearGradient></defs></svg>
  <div class="absolute inset-0 flex flex-col items-center justify-center"><span class="text-3xl font-bold">${pct}%</span><span class="text-xs text-slate-400">${r.classification}</span></div></div>
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8 text-sm">
  <div class="bg-dark-800 rounded-xl p-3"><div class="text-slate-400">Correct</div><div class="text-xl font-bold text-green-400">${r.correct}</div></div>
  <div class="bg-dark-800 rounded-xl p-3"><div class="text-slate-400">Incorrect</div><div class="text-xl font-bold text-red-400">${r.incorrect}</div></div>
  <div class="bg-dark-800 rounded-xl p-3"><div class="text-slate-400">Unanswered</div><div class="text-xl font-bold text-yellow-400">${r.unanswered}</div></div>
  <div class="bg-dark-800 rounded-xl p-3"><div class="text-slate-400">Time</div><div class="text-xl font-bold text-cyan-400">${formatTime(r.time_taken_seconds)}</div></div></div>
  <div class="text-slate-300 mb-2">Marks: <span class="font-bold text-white">${r.marks_obtained} / ${r.total_marks}</span></div>
  <div class="flex flex-wrap justify-center gap-3 mt-8"><button onclick="navigate('analytics')" class="btn-primary px-6 py-2.5 rounded-xl text-white text-sm">View Analytics</button>
  <button onclick="navigate('student-dash')" class="btn-outline px-6 py-2.5 rounded-xl text-sm">Dashboard</button><button onclick="navigate('quizzes')" class="btn-outline px-6 py-2.5 rounded-xl text-sm">More Quizzes</button></div></div>
  ${r.questions?`<div class="glass rounded-xl p-6 mt-6"><h2 class="font-semibold mb-4">Answer Review</h2><div class="space-y-4">${r.questions.map((q,i)=>`<div class="border border-white/5 rounded-xl p-4"><div class="flex justify-between text-sm mb-2"><span class="text-slate-400">Q${i+1}</span><span class="${q.is_correct?'text-green-400':'text-red-400'}">${q.is_correct?'Correct':'Incorrect'}</span></div><p class="mb-3">${q.text}</p>
  <div class="space-y-1 text-sm">${q.options.map(o=>`<div class="px-3 py-1.5 rounded-lg ${o.is_correct?'bg-green-500/15 text-green-300':o.id===q.selected_option_id?'bg-red-500/15 text-red-300':'text-slate-400'}">${o.is_correct?'✓ ':o.id===q.selected_option_id?'✗ ':''}${o.text}</div>`).join('')}</div>
  ${q.explanation?`<p class="text-xs text-slate-400 mt-2"><i class="fas fa-info-circle mr-1"></i>${q.explanation}</p>`:''}</div>`).join('')}</div></div>`:''}</div>`;
}

function renderAnalytics() {
  return `${navbar('analytics')}<div class="max-w-7xl mx-auto px-4 sm:px-6 py-8 fade-in"><h1 class="text-2xl font-bold mb-6">Performance Analytics</h1><div id="analytics-content"><div class="text-center py-20 text-slate-400"><i class="fas fa-spinner fa-spin text-2xl"></i></div></div></div>`;
}

async function loadAnalytics() {
  try {
    const a = await api('/student/analytics'); const c=$('#analytics-content');
    if(a.score_stats.total_attempts===0){ c.innerHTML='<div class="glass rounded-xl p-12 text-center text-slate-400">No quiz data yet. Take a quiz!</div>'; return; }
    c.innerHTML=`<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
    <div class="glass rounded-xl p-5"><div class="text-xs text-slate-400 uppercase">Attempts</div><div class="text-2xl font-bold mt-1">${a.score_stats.total_attempts}</div></div>
    <div class="glass rounded-xl p-5"><div class="text-xs text-slate-400 uppercase">Average</div><div class="text-2xl font-bold mt-1 text-purple-400">${a.score_stats.average_score}%</div></div>
    <div class="glass rounded-xl p-5"><div class="text-xs text-slate-400 uppercase">Highest</div><div class="text-2xl font-bold mt-1 text-cyan-400">${a.score_stats.highest_score}%</div></div>
    <div class="glass rounded-xl p-5"><div class="text-xs text-slate-400 uppercase">Lowest</div><div class="text-2xl font-bold mt-1 text-yellow-400">${a.score_stats.lowest_score}%</div></div></div>
    <div class="grid lg:grid-cols-2 gap-6 mb-6"><div class="glass rounded-xl p-6"><h3 class="font-semibold mb-4">Score Distribution</h3><canvas id="dist-chart" height="180"></canvas></div>
    <div class="glass rounded-xl p-6"><h3 class="font-semibold mb-4">Subject-wise Performance</h3><canvas id="subj-chart" height="180"></canvas></div></div>
    <div class="grid lg:grid-cols-2 gap-6 mb-6"><div class="glass rounded-xl p-6"><h3 class="font-semibold mb-4">Progress Over Time</h3><canvas id="prog-chart" height="180"></canvas></div>
    <div class="glass rounded-xl p-6"><h3 class="font-semibold mb-4">Topic Accuracy</h3><div class="space-y-3 max-h-64 overflow-y-auto scrollbar-thin">${a.topic_wise.length?a.topic_wise.map(t=>`<div><div class="flex justify-between text-sm mb-1"><span>${t.topic} <span class="text-slate-500">(${t.subject})</span></span><span class="${t.accuracy>=70?'text-green-400':t.accuracy>=50?'text-yellow-400':'text-red-400'}">${t.accuracy}%</span></div>
    <div class="h-2 bg-dark-700 rounded-full overflow-hidden"><div class="h-full rounded-full ${t.accuracy>=70?'bg-green-500':t.accuracy>=50?'bg-yellow-500':'bg-red-500'}" style="width:${t.accuracy}%"></div></div></div>`).join(''):'<p class="text-slate-500 text-sm">No topic data</p>'}</div></div></div>
    <div class="glass rounded-xl p-6"><h3 class="font-semibold mb-3"><i class="fas fa-lightbulb text-yellow-400 mr-2"></i>Recommendations</h3><ul class="space-y-2 text-sm text-slate-300">${a.recommendations.map(r=>`<li class="flex gap-2"><span class="text-cyan-400">→</span>${r}</li>`).join('')}</ul></div>`;
    const dist=a.score_distribution;
    state.charts.dist=new Chart($('#dist-chart'),{type:'doughnut',data:{labels:Object.keys(dist),datasets:[{data:Object.values(dist),backgroundColor:['#ef4444','#f97316','#eab308','#22c55e','#a855f7'],borderWidth:0}]},options:{plugins:{legend:{position:'bottom',labels:{color:'#94a3b8',boxWidth:12}}}}});
    if(a.subject_wise.length) state.charts.subj=new Chart($('#subj-chart'),{type:'bar',data:{labels:a.subject_wise.map(s=>s.subject),datasets:[{label:'Avg %',data:a.subject_wise.map(s=>s.average_score),backgroundColor:'#a855f7',borderRadius:6}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#64748b'},grid:{display:false}},y:{min:0,max:100,ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,0.04)'}}}}});
    if(a.progress_over_time.length) state.charts.prog=new Chart($('#prog-chart'),{type:'line',data:{labels:a.progress_over_time.map(p=>p.quiz?.slice(0,15)||''),datasets:[{data:a.progress_over_time.map(p=>p.percentage),borderColor:'#22d3ee',backgroundColor:'rgba(34,211,238,0.1)',fill:true,tension:0.3}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,0.04)'}},y:{min:0,max:100,ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,0.04)'}}}}});
  } catch(e){ $('#analytics-content').innerHTML=`<p class="text-red-400">${e.message}</p>`; }
}

function renderHistory() {
  return `${navbar('history')}<div class="max-w-5xl mx-auto px-4 py-8 fade-in"><h1 class="text-2xl font-bold mb-6">Quiz History</h1><div id="history-list" class="glass rounded-xl overflow-hidden">Loading...</div></div>`;
}

async function loadHistory() {
  try {
    const list=await api('/student/history'); const el=$('#history-list');
    if(!list.length){ el.innerHTML='<p class="p-8 text-slate-500 text-center">No history yet.</p>'; return; }
    el.innerHTML=`<table class="w-full text-sm"><thead class="bg-dark-800 text-slate-400 text-left"><tr><th class="px-4 py-3">Quiz</th><th class="px-4 py-3">Subject</th><th class="px-4 py-3">Score</th><th class="px-4 py-3">Time</th><th class="px-4 py-3">Date</th><th class="px-4 py-3"></th></tr></thead>
    <tbody>${list.map(a=>`<tr class="border-t border-white/5 hover:bg-white/5"><td class="px-4 py-3 font-medium">${a.quiz_title}</td><td class="px-4 py-3 text-slate-400">${a.subject||'—'}</td>
    <td class="px-4 py-3"><span class="${a.percentage>=70?'text-green-400':a.percentage>=50?'text-yellow-400':'text-red-400'} font-semibold">${a.percentage}%</span></td>
    <td class="px-4 py-3 text-slate-400">${formatTime(a.time_taken_seconds)}</td><td class="px-4 py-3 text-slate-400">${a.submitted_at?new Date(a.submitted_at).toLocaleDateString():'—'}</td>
    <td class="px-4 py-3"><button onclick="viewResult(${a.id})" class="text-purple-400 hover:underline text-xs">View</button></td></tr>`).join('')}</tbody></table>`;
  } catch(e){ $('#history-list').innerHTML=`<p class="p-4 text-red-400">${e.message}</p>`; }
}

async function viewResult(id){ try{ state.result=await api(`/attempts/${id}/result`); navigate('result'); }catch(e){ alert(e.message); } }

function renderTeacherDash() {
  return `${navbar('teacher-dash')}<div class="max-w-7xl mx-auto px-4 sm:px-6 py-8 fade-in"><div class="flex justify-between items-center mb-6"><h1 class="text-2xl font-bold">Teacher Dashboard</h1>
  <button onclick="navigate('create-quiz')" class="btn-primary px-5 py-2.5 rounded-xl text-white text-sm"><i class="fas fa-plus mr-1"></i> Create Quiz</button></div>
  <div id="teacher-quizzes" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">Loading...</div></div>`;
}

async function loadTeacherDash() {
  try {
    const quizzes=await api('/teacher/quizzes'); const el=$('#teacher-quizzes');
    if(!quizzes.length){ el.innerHTML='<p class="text-slate-500 col-span-full">No quizzes yet. Create one!</p>'; return; }
    el.innerHTML=quizzes.map(q=>`<div class="glass glass-hover rounded-xl p-5 transition"><div class="flex justify-between mb-2"><span class="text-xs px-2 py-0.5 rounded-full ${q.is_published?'bg-green-500/20 text-green-300':'bg-yellow-500/20 text-yellow-300'}">${q.is_published?'Published':'Draft'}</span><span class="text-xs text-slate-500">${q.difficulty}</span></div>
    <h3 class="font-semibold mb-1">${q.title}</h3><p class="text-slate-400 text-sm mb-3">${q.subject?.name||''} · ${q.question_count||0} questions · ${q.total_marks} marks</p>
    <div class="flex gap-2">${!q.is_published?`<button onclick="publishQuiz(${q.id})" class="text-xs btn-primary px-3 py-1.5 rounded-lg text-white">Publish</button>`:''}
    <button onclick="viewQuizResults(${q.id})" class="text-xs btn-outline px-3 py-1.5 rounded-lg">Results</button>
    <button onclick="exportCSV(${q.id})" class="text-xs text-slate-400 hover:text-cyan-400 px-2">CSV</button>
    <button onclick="deleteQuiz(${q.id})" class="text-xs text-red-400 hover:text-red-300 px-2 ml-auto"><i class="fas fa-trash"></i></button></div></div>`).join('');
  } catch(e){ $('#teacher-quizzes').innerHTML=`<p class="text-red-400">${e.message}</p>`; }
}

async function publishQuiz(id){ try{ await api(`/teacher/quizzes/${id}`,{method:'PATCH',body:JSON.stringify({is_published:true})}); loadTeacherDash(); }catch(e){ alert(e.message); } }
async function deleteQuiz(id){ if(!confirm('Delete this quiz?')) return; try{ await api(`/teacher/quizzes/${id}`,{method:'DELETE'}); loadTeacherDash(); }catch(e){ alert(e.message); } }
function viewQuizResults(id){ state.selectedQuizId=id; navigate('quiz-results'); }
function exportCSV(id){ fetch(`${API}/teacher/export/${id}`,{headers:{Authorization:`Bearer ${state.token}`}}).then(r=>r.blob()).then(b=>{ const url=URL.createObjectURL(b); const a=document.createElement('a'); a.href=url; a.download=`quiz_${id}_results.csv`; a.click(); }); }

function renderTeacherResults() {
  return `${navbar('teacher-dash')}<div class="max-w-6xl mx-auto px-4 py-8 fade-in"><button onclick="navigate('teacher-dash')" class="text-sm text-slate-400 hover:text-white mb-4">← Back</button><div id="t-results">Loading...</div></div>`;
}

async function loadTeacherResults() {
  try {
    const d=await api(`/teacher/quizzes/${state.selectedQuizId}/results`); const el=$('#t-results');
    el.innerHTML=`<h1 class="text-2xl font-bold mb-2">${d.quiz.title}</h1><p class="text-slate-400 mb-6">${d.attempts.length} submissions · Class avg: ${d.class_average.average}%</p>
    <div class="grid sm:grid-cols-3 gap-4 mb-6"><div class="glass rounded-xl p-4 text-center"><div class="text-2xl font-bold text-purple-400">${d.class_average.average}%</div><div class="text-xs text-slate-400">Class Average</div></div>
    <div class="glass rounded-xl p-4 text-center"><div class="text-2xl font-bold text-cyan-400">${d.class_average.highest}%</div><div class="text-xs text-slate-400">Highest</div></div>
    <div class="glass rounded-xl p-4 text-center"><div class="text-2xl font-bold text-yellow-400">${d.class_average.lowest}%</div><div class="text-xs text-slate-400">Lowest</div></div></div>
    ${d.weak_topics.length?`<div class="glass rounded-xl p-5 mb-6"><h3 class="font-semibold mb-3">Commonly Misunderstood Topics</h3><div class="flex flex-wrap gap-2">${d.weak_topics.map(t=>`<span class="px-3 py-1 rounded-full bg-red-500/15 text-red-300 text-sm">${t.topic} (${t.accuracy}%)</span>`).join('')}</div></div>`:''}
    <div class="glass rounded-xl overflow-hidden"><table class="w-full text-sm"><thead class="bg-dark-800 text-slate-400 text-left"><tr><th class="px-4 py-3">#</th><th class="px-4 py-3">Student</th><th class="px-4 py-3">Score</th><th class="px-4 py-3">Time</th><th class="px-4 py-3">Submitted</th></tr></thead>
    <tbody>${d.attempts.map((a,i)=>`<tr class="border-t border-white/5"><td class="px-4 py-3 text-slate-500">${i+1}</td><td class="px-4 py-3">${a.student_name}<div class="text-xs text-slate-500">${a.student_email}</div></td>
    <td class="px-4 py-3 font-semibold ${a.percentage>=70?'text-green-400':a.percentage>=50?'text-yellow-400':'text-red-400'}">${a.percentage}%</td>
    <td class="px-4 py-3 text-slate-400">${formatTime(a.time_taken_seconds)}</td><td class="px-4 py-3 text-slate-400">${a.submitted_at?new Date(a.submitted_at).toLocaleString():'—'}</td></tr>`).join('')||'<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500">No submissions yet</td></tr>'}</tbody></table></div>`;
  } catch(e){ $('#t-results').innerHTML=`<p class="text-red-400">${e.message}</p>`; }
}

function renderCreateQuiz() {
  return `${navbar('create-quiz')}<div class="max-w-3xl mx-auto px-4 py-8 fade-in"><h1 class="text-2xl font-bold mb-6">Create New Quiz</h1>
  <form id="create-quiz-form" class="space-y-5"><div class="glass rounded-xl p-6 space-y-4">
  <div><label class="text-sm text-slate-400">Title</label><input name="title" required class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5 focus:outline-none focus:border-purple-500" /></div>
  <div><label class="text-sm text-slate-400">Description</label><textarea name="description" rows="2" class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5 focus:outline-none focus:border-purple-500"></textarea></div>
  <div class="grid sm:grid-cols-3 gap-4"><div><label class="text-sm text-slate-400">Subject</label><select name="subject_id" id="subject-select" class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-3 py-2.5"></select></div>
  <div><label class="text-sm text-slate-400">Difficulty</label><select name="difficulty" class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-3 py-2.5"><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></div>
  <div><label class="text-sm text-slate-400">Duration (min)</label><input name="duration_minutes" type="number" value="15" min="5" class="w-full mt-1 bg-dark-800 border border-white/10 rounded-lg px-4 py-2.5" /></div></div></div>
  <div class="glass rounded-xl p-6"><div class="flex justify-between items-center mb-4"><h2 class="font-semibold">Questions</h2><button type="button" onclick="addQuestion()" class="text-sm text-purple-400 hover:underline"><i class="fas fa-plus mr-1"></i>Add Question</button></div>
  <div id="questions-container" class="space-y-4"></div></div>
  <div id="create-error" class="text-red-400 text-sm hidden"></div>
  <button type="submit" class="btn-primary w-full py-3 rounded-xl text-white font-semibold">Create Quiz (Draft)</button></form></div>`;
}

function addQuestion() {
  const container=$('#questions-container'); if(!container) return; const idx=container.children.length;
  const div=document.createElement('div'); div.className='border border-white/10 rounded-xl p-4 question-block'; div.dataset.idx=idx;
  div.innerHTML=`<div class="flex justify-between mb-2"><span class="text-sm font-medium text-slate-400">Question ${idx+1}</span><button type="button" onclick="this.closest('.question-block').remove()" class="text-red-400 text-xs"><i class="fas fa-times"></i></button></div>
  <input name="q_text" required placeholder="Question text" class="w-full bg-dark-800 border border-white/10 rounded-lg px-3 py-2 text-sm mb-2 focus:outline-none focus:border-purple-500" />
  <div class="grid grid-cols-2 gap-2 mb-2">${[0,1,2,3].map(i=>`<div class="flex items-center gap-2"><input type="radio" name="correct_${idx}" value="${i}" ${i===0?'checked':''} class="accent-purple-500" /><input name="opt_${idx}_${i}" required placeholder="Option ${i+1}" class="flex-1 bg-dark-800 border border-white/10 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:border-purple-500" /></div>`).join('')}</div>
  <input name="q_expl" placeholder="Explanation (optional)" class="w-full bg-dark-800 border border-white/10 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-purple-500" />`;
  container.appendChild(div);
}

async function loadSubjectsForCreate(){ try{ const subjects=await api('/subjects'); const sel=$('#subject-select'); if(sel) sel.innerHTML=subjects.map(s=>`<option value="${s.id}">${s.name}</option>`).join(''); }catch(e){} }

function bindEvents() {
  const form=$('#auth-form');
  if(form) form.onsubmit=async e=>{ e.preventDefault(); const fd=new FormData(form); const body=Object.fromEntries(fd); const err=$('#auth-error');
    try{ const path=state.page==='login'?'/auth/login':'/auth/register'; const data=await api(path,{method:'POST',body:JSON.stringify(body)}); state.token=data.access_token; state.user=data.user; localStorage.setItem('sq_token',state.token); navigate(data.user.role==='teacher'?'teacher-dash':'student-dash'); }
    catch(ex){ err.textContent=ex.message; err.classList.remove('hidden'); } };
  const cq=$('#create-quiz-form');
  if(cq) cq.onsubmit=async e=>{ e.preventDefault(); const fd=new FormData(cq); const blocks=[...document.querySelectorAll('.question-block')];
    const questions=blocks.map((b,idx)=>{ const text=b.querySelector('[name=q_text]').value; const expl=b.querySelector('[name=q_expl]').value;
      const correctIdx=parseInt(b.querySelector(`input[name=correct_${b.dataset.idx||idx}]:checked`)?.value||0);
      const options=[0,1,2,3].map(i=>({text:b.querySelector(`[name=opt_${b.dataset.idx||idx}_${i}]`).value,is_correct:i===correctIdx,order:i}));
      return {text,explanation:expl||null,marks:1,order:idx,options}; });
    const body={title:fd.get('title'),description:fd.get('description')||null,subject_id:parseInt(fd.get('subject_id')),difficulty:fd.get('difficulty'),duration_minutes:parseInt(fd.get('duration_minutes')),questions};
    try{ await api('/teacher/quizzes',{method:'POST',body:JSON.stringify(body)}); navigate('teacher-dash'); }catch(ex){ const err=$('#create-error'); err.textContent=ex.message; err.classList.remove('hidden'); } };
}

async function init() {
  if(state.token){ try{ state.user=await api('/auth/me'); navigate(state.user.role==='teacher'?'teacher-dash':'student-dash'); return; }catch(e){ localStorage.removeItem('sq_token'); state.token=null; } }
  navigate('landing');
}
init();
