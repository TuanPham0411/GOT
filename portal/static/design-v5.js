document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('h1,h2,h3,legend').forEach(el=>{
    const nodes=[...el.childNodes].reverse();
    for(const node of nodes){
      if(node.nodeType!==Node.TEXT_NODE) continue;
      const clean=node.textContent.replace(/[.。]\s*$/,'');
      if(clean!==node.textContent) node.textContent=clean;
      if(clean.trim()) break;
    }
  });
});
