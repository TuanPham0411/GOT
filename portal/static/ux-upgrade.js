(()=>{
  const header=document.querySelector('.site-header');
  const nav=header?.querySelector('nav');
  if(!header||!nav)return;

  const path=location.pathname.replace(/\/$/,'')||'/';
  [...nav.querySelectorAll('a[href^="/"]')].forEach(link=>{
    const href=(link.getAttribute('href')||'').replace(/\/$/,'')||'/';
    if(href==='/'?path==='/':path===href||path.startsWith(href+'/'))link.setAttribute('aria-current','page');
  });

  const toggle=document.createElement('button');
  toggle.type='button';
  toggle.className='nav-toggle';
  toggle.setAttribute('aria-label','Mở menu');
  toggle.setAttribute('aria-expanded','false');
  toggle.innerHTML='<span></span>';
  header.insertBefore(toggle,nav);
  const closeNav=()=>{header.classList.remove('nav-open');toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-label','Mở menu')};
  toggle.addEventListener('click',()=>{const open=header.classList.toggle('nav-open');toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-label',open?'Đóng menu':'Mở menu')});
  nav.addEventListener('click',e=>{if(e.target.closest('a'))closeNav()});
  addEventListener('resize',()=>{if(innerWidth>900)closeNav()},{passive:true});

  const tools=header.querySelector('.head-tools');
  if(tools){
    const locale=document.createElement('div');
    locale.className='locale-switch';
    locale.hidden=true;
    locale.setAttribute('aria-label','Ngôn ngữ');
    const current=(document.documentElement.lang||'vi').toLowerCase();
    locale.innerHTML=`<a href="/language/vi" class="${current==='vi'?'active':''}" aria-label="Tiếng Việt">VI</a><a href="/language/en" class="${current==='en'?'active':''}" aria-label="English">EN</a>`;
    tools.prepend(locale);

    const identity=tools.querySelector('.identity');
    if(identity){
      const box=document.createElement('div');
      box.className='account-actions';
      identity.parentNode.insertBefore(box,identity);
      box.append(identity);
      identity.setAttribute('aria-haspopup','true');
      identity.setAttribute('aria-expanded','false');
      const menu=document.createElement('div');
      menu.className='account-menu';
      menu.innerHTML='<a href="/account">TÀI KHOẢN & THIẾT BỊ</a><form method="post" action="/logout"><button type="submit">ĐĂNG XUẤT</button></form>';
      box.append(menu);
      identity.addEventListener('click',e=>{if(box.classList.contains('open'))return;e.preventDefault();box.classList.add('open');identity.setAttribute('aria-expanded','true')});
      document.addEventListener('click',e=>{if(!box.contains(e.target)){box.classList.remove('open');identity.setAttribute('aria-expanded','false')}});
      document.addEventListener('keydown',e=>{if(e.key==='Escape'){box.classList.remove('open');identity.setAttribute('aria-expanded','false');closeNav()}});
    }
  }

  document.querySelectorAll('a[target="_blank"]').forEach(a=>a.rel='noopener noreferrer');
  document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',()=>{
    const button=form.querySelector('button[type="submit"],button:not([type])');
    if(button&&!button.disabled){button.classList.add('is-busy');button.setAttribute('aria-busy','true')}
  }));
})();
