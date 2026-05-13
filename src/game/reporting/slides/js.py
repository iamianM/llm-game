"""JavaScript for the slide deck review packet."""

SLIDE_JS = """
const slides=[...document.querySelectorAll('.slide')];
const dots=[...document.querySelectorAll('[data-scene-target]')];
let current=0;
function showSlide(index){
  if(!slides.length)return;
  current=Math.max(0,Math.min(index,slides.length-1));
  slides.forEach((s,i)=>s.classList.toggle('active',i===current));
  dots.forEach((d,i)=>d.classList.toggle('active',i===current));
  const side=document.querySelector('.side-panel');
  const state=slides[current].querySelector('[data-state-panel]');
  if(side&&state){side.innerHTML=state.innerHTML;}
}
dots.forEach((d,i)=>d.addEventListener('click',()=>showSlide(i)));
document.querySelector('[data-next]')?.addEventListener('click',()=>showSlide(current+1));
document.querySelector('[data-prev]')?.addEventListener('click',()=>showSlide(current-1));
document.addEventListener('keydown',event=>{
  if(event.key==='ArrowRight')showSlide(current+1);
  if(event.key==='ArrowLeft')showSlide(current-1);
});
document.addEventListener('click',event=>{
  const open=event.target.closest('[data-open-dialog]');
  if(open){
    const dialog=document.getElementById(open.dataset.openDialog);
    if(dialog&&dialog.showModal)dialog.showModal();
  }
  if(event.target.matches('[data-close-dialog]')){
    event.target.closest('dialog')?.close();
  }
});
showSlide(0);
"""
