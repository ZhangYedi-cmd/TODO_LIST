(function(){
  var cases = document.querySelectorAll('.case');
  var idx = document.getElementById('page-index');

  function show(target){
    if(target === '' || target === '/' || !target){
      idx.hidden = false;
      cases.forEach(function(c){ c.hidden = true; });
      window.scrollTo(0,0);
    } else {
      var el = document.getElementById('case-' + target);
      if(el){
        idx.hidden = true;
        cases.forEach(function(c){ c.hidden = (c !== el); });
        window.scrollTo(0,0);
      } else {
        // 找不到对应档案，回到目录
        location.hash = '';
      }
    }
  }

  window.addEventListener('hashchange', function(){
    var h = (location.hash || '').replace(/^#/, '').replace(/\//g, '');
    show(h);
  });

  // 初始
  var initHash = (location.hash || '').replace(/^#/, '').replace(/\//g, '');
  show(initHash);

  // ===== 目录页搜索 + 筛选 =====
  var q = document.getElementById('q');
  var btns = document.querySelectorAll('.fbtn');
  var cards = document.querySelectorAll('.card-c');
  var empty = document.getElementById('empty');
  var filter = 'all';

  function run(){
    var v = (q.value || '').trim().toLowerCase();
    var visible = 0;
    cards.forEach(function(c){
      var pricing = (c.querySelector('.chip.pri') || {}).textContent || '';
      var ok = (filter === 'all' || pricing === filter) && (!v || (c.dataset.search || '').indexOf(v) >= 0);
      c.style.display = ok ? '' : 'none';
      if(ok) visible++;
    });
    empty.style.display = visible ? 'none' : '';
  }

  if(q) q.addEventListener('input', run);
  btns.forEach(function(b){
    b.addEventListener('click', function(){
      btns.forEach(function(x){ x.classList.remove('on'); });
      b.classList.add('on');
      filter = b.dataset.f;
      run();
    });
  });
})();
