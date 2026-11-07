const $ = (s) => document.querySelector(s);
const views = ["chat","gis","remote","survey","coding","projects","settings"];
const titles = {chat:"المساعد الذكي",gis:"GIS والجيوماتكس",remote:"الاستشعار عن بُعد",survey:"المساحة والرفع",coding:"استوديو البرمجة",projects:"المشروعات والملفات",settings:"الإعدادات"};
let projects = JSON.parse(localStorage.getItem("gm_projects") || "[]");

function showView(name){
  document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));
  $("#view-"+name)?.classList.add("active");
  document.querySelectorAll(".nav-item[data-view]").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
  $("#topTitle").textContent = titles[name] || "GEO MIND AI";
  $("#sidebar").classList.remove("open");
}
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));
$("#menuBtn").addEventListener("click",()=>$("#sidebar").classList.toggle("open"));
$("#newChat").addEventListener("click",()=>{ $("#messages").innerHTML=""; $("#welcome").style.display="block"; showView("chat"); });
$("#themeBtn").addEventListener("click",()=>document.body.classList.toggle("light"));
document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{ $("#promptInput").value=b.dataset.prompt; $("#promptInput").focus(); }));
function addMessage(role,text){
  $("#welcome").style.display="none";
  const el=document.createElement("div"); el.className="message "+role;
  const who=document.createElement("span"); who.className="who"; who.textContent=role==="user"?"أنت":"GEO MIND AI";
  const body=document.createElement("div"); body.textContent=text;
  el.append(who,body); $("#messages").append(el); $("#messages").scrollTop=$("#messages").scrollHeight;
}
async function sendPrompt(prompt){
  addMessage("user",prompt);
  const url=(localStorage.getItem("gm_api_url")||"").replace(/\/$/,"");
  if(!url){
    addMessage("assistant","واجهة GEO MIND AI تعمل بنجاح، لكن محرك الذكاء الاصطناعي لم يتم ربطه بعد.\n\nالخطوة التالية: نشر Backend ثم وضع رابط API في الإعدادات. لن أدّعي تنفيذ تحليل أو تشغيل كود قبل تفعيل المحرك.");
    return;
  }
  const loading="جارٍ الاتصال بالمحرك...";
  addMessage("assistant",loading);
  const last=$("#messages").lastElementChild;
  try{
    const res=await fetch(url+"/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:prompt})});
    if(!res.ok) throw new Error("HTTP "+res.status);
    const data=await res.json();
    last.lastElementChild.textContent=data.reply || "وصل رد فارغ من المحرك.";
  }catch(e){
    last.lastElementChild.textContent="تعذر الاتصال بمحرك الذكاء الاصطناعي. راجع رابط الخادم وحالة النشر. التفاصيل: "+e.message;
  }
}
$("#chatForm").addEventListener("submit",e=>{e.preventDefault();const p=$("#promptInput").value.trim();if(!p)return;$("#promptInput").value="";sendPrompt(p);});
function renderProjects(){
  const list=$("#projectList"); list.innerHTML="";
  if(!projects.length){list.innerHTML='<p class="muted">لا توجد مشروعات محفوظة بعد.</p>';return;}
  projects.forEach((p,i)=>{const d=document.createElement("div");d.className="project-item";d.textContent=p;list.append(d);});
}
$("#addProject").addEventListener("click",()=>{const v=$("#projectName").value.trim();if(!v)return;projects.unshift(v);localStorage.setItem("gm_projects",JSON.stringify(projects));$("#projectName").value="";renderProjects();});
$("#saveSettings").addEventListener("click",()=>{const v=$("#apiUrl").value.trim();localStorage.setItem("gm_api_url",v);localStorage.setItem("gm_display_name",$("#displayName").value.trim());$("#connectionText").textContent=v?"تم حفظ رابط المحرك":"الواجهة تعمل محليًا";alert("تم حفظ الإعدادات على هذا الجهاز.");});
$("#apiUrl").value=localStorage.getItem("gm_api_url")||"";
renderProjects();
if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));}
