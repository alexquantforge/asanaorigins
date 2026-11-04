const fs=require('fs'), path=require('path'); const {JSDOM}=require('jsdom');
function pages(d,o=[]){for(const e of fs.readdirSync(d,{withFileTypes:true})){if(e.name==='node_modules'||e.name.startsWith('.'))continue;const p=path.join(d,e.name);if(e.isDirectory())pages(p,o);else if(e.name==='index.html')o.push(p);}return o;}
const needle='гомукхам';
for(const f of pages('.')){
  const doc=new JSDOM(fs.readFileSync(f,'utf8')).window.document;
  // найти самую длинную текстовую ноду, содержащую отрывок стиха
  const walker=doc.createTreeWalker(doc.body, 4 /*TEXT*/);
  let n;
  while((n=walker.nextNode())){
    if(n.textContent.includes('савйе') && n.textContent.includes('прачакшате')){
      const el=n.parentElement;
      const chain=[]; let e=el;
      while(e && e!==doc.body){ chain.push(e.tagName.toLowerCase()+(e.className?'.'+String(e.className).replace(/\s+/g,'.'):'')); e=e.parentElement; }
      console.log(f, '\n   ', chain.slice(0,5).join(' ← '), '\n    длина текста:', n.textContent.trim().length);
    }
  }
}
