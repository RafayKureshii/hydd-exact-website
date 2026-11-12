/* HYDD enhancement layer. No API keys, user tracking or remote JavaScript. */
(()=>{
  'use strict';
  const PHONE='33765849546'; // Confirm this is the business's WhatsApp account.
  const locale=(()=>{let seg=location.pathname.split('/').filter(Boolean)[0]; return ['en','ar'].includes(seg)?seg:'fr';})();
  const locales={fr:'Français',en:'English',ar:'العربية'};
  const enabled=(document.querySelector('meta[name="hydd-built-languages"]')?.content||'fr').split(',');
  const greetings={
    fr:'Bonjour HYDD, je souhaite obtenir des renseignements sur ',
    en:'Hello HYDD, I would like information about ',
    ar:'مرحباً HYDD، أود الاستفسار عن '
  };
  const services={
    '/mise-disposition':{fr:'le service de chauffeur dédié',en:'your dedicated chauffeur service',ar:'خدمة السائق الخاص'},
    '/digital-products-1-1':{fr:'les transferts aéroport et gare',en:'airport and train-station transfers',ar:'خدمة النقل من وإلى المطار ومحطات القطار'},
    '/vip':{fr:"l'accueil VIP",en:'VIP airport welcome',ar:'خدمة الاستقبال لكبار الشخصيات'},
    '/evnements':{fr:'vos services événementiels',en:'event transport services',ar:'خدمات نقل الفعاليات'},
    '/excursions':{fr:'les escapades privées',en:'private excursions',ar:'الرحلات الخاصة'},
    '/coner':{fr:'le service de conciergerie',en:'luxury concierge services',ar:'خدمات الكونسيرج الفاخرة'},
    '/guard':{fr:'la protection rapprochée',en:'executive protection',ar:'خدمات الحماية الشخصية'}
  };
  function originalPath(){
    let p=location.pathname.replace(/^\/(en|ar)(?=\/|$)/,'');
    return (p||'/').replace(/\/$/,'')||'/';
  }
  function localizedPath(language){
    const path=originalPath();
    return (language==='fr'?'':'/'+language)+(path==='/'?'/':path+'/');
  }
  function langPicker(){
    // HYDD_VISIBLE_DROPDOWN_V2: keep the exact captured header trigger.
    // Show the choices in a body-level popup, not in Squarespace's clipped or
    // invisible native dropdown, so legacy header styles cannot hide labels.
    const names={fr:'Français',en:'English',ar:'العربية'};
    const choices=['fr','en','ar'].filter(code=>enabled.includes(code));
    if(choices.length<2)return;
    const candidates=Array.from(document.querySelectorAll(
      '.header .language-picker, .header-actions .language-picker, '+
      '.language-picker-desktop, .language-picker-mobile, '+
      '#multilingual-language-picker-desktop, #multilingual-language-picker-mobile, '+
      '.header .hydd-native-language-switcher'
    ));
    const roots=candidates.filter(node=>!candidates.some(other=>other!==node&&node.contains(other)));
    if(!roots.length){
      const header=document.querySelector('.header-actions') ||
                   document.querySelector('.header-menu-actions') ||
                   document.querySelector('header');
      if(!header)return;
      const root=document.createElement('div');
      root.className='hydd-header-language-fallback';
      const button=document.createElement('button');
      button.type='button';button.className='hydd-header-language-button';
      button.setAttribute('aria-haspopup','menu');
      button.innerHTML='<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.4 3 14.6 0 18M12 3c-3 3.4-3 14.6 0 18"/></svg><span class="current-language-name"></span><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>';
      root.append(button);header.append(root);roots.push(root);
    }

    // Exactly one popup for both desktop and mobile controls; not a second
    // language button. Appending outside the header avoids overflow:hidden,
    // opacity, transforms, and color inheritance from captured Squarespace.
    document.getElementById('hydd-visible-language-menu')?.remove();
    const panel=document.createElement('div');
    panel.id='hydd-visible-language-menu';
    panel.setAttribute('role','menu');
    panel.setAttribute('aria-label', {fr:'Choisir la langue',en:'Choose language',ar:'اختر اللغة'}[locale]);
    panel.setAttribute('dir','ltr');
    panel.hidden=true;
    choices.forEach(code=>{
      const a=document.createElement('a');
      a.textContent=names[code];
      a.href=localizedPath(code)+location.search+location.hash;
      a.lang=code;
      a.dir=code==='ar'?'rtl':'ltr';
      a.setAttribute('role','menuitem');
      if(code===locale){a.classList.add('hydd-language-current');a.setAttribute('aria-current','page');}
      panel.append(a);
    });
    document.body.append(panel);
    window.__HYDD_LANGUAGE_MENU_VERSION__='visible-v2';

    let activeRoot=null;
    const triggers=new Map();
    function close(){
      panel.hidden=true;
      for(const trigger of triggers.values())trigger.setAttribute('aria-expanded','false');
      activeRoot=null;
    }
    function position(root){
      // Match the position beneath the original header switcher.
      const anchor=triggers.get(root)||root;
      const rect=anchor.getBoundingClientRect();
      const width=Math.min(220,window.innerWidth-16);
      const left=Math.max(8,Math.min(rect.right-width,window.innerWidth-width-8));
      panel.style.setProperty('width',width+'px','important');
      panel.style.setProperty('left',left+'px','important');
      // If the menu would overflow below the viewport, show it above.
      const height=panel.getBoundingClientRect().height||choices.length*44+12;
      const below=rect.bottom+6;
      panel.style.setProperty('top',(below+height>window.innerHeight-8&&rect.top>height+12 ? rect.top-height-6 : below)+'px','important');
    }
    function open(root){
      if(activeRoot===root&&!panel.hidden){close();return;}
      activeRoot=root;
      panel.hidden=false;
      position(root);
      for(const [r,trigger] of triggers)trigger.setAttribute('aria-expanded',String(r===root));
    }
    roots.forEach(root=>{
      if(root.dataset.hyddVisibleDropdown==='v2')return;
      root.dataset.hyddVisibleDropdown='v2';
      root.classList.add('hydd-native-language-switcher');
      const current=root.querySelector('.current-language-name');
      if(current)current.textContent=names[locale];
      const trigger=root.querySelector('.hydd-header-language-button, .language-picker-button, .language-picker-toggle, .language-picker-header, [aria-haspopup], button')||root;
      triggers.set(root,trigger);
      trigger.setAttribute('aria-haspopup','menu');
      trigger.setAttribute('aria-expanded','false');
      if(trigger===root&&!root.hasAttribute('tabindex'))root.setAttribute('tabindex','0');
      // Disable Squarespace's empty or non-functional translation panel.
      root.querySelectorAll('.language-picker-content, .language-picker-dropdown, .language-picker-list').forEach(el=>{
        el.hidden=true;
        el.setAttribute('aria-hidden','true');
      });
      root.addEventListener('click',event=>{
        if(event.target.closest('#hydd-visible-language-menu'))return;
        event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();
        open(root);
      },true);
      root.addEventListener('keydown',event=>{
        if(event.key==='Escape'){close();return;}
        if(event.key==='Enter'||event.key===' '||event.key==='ArrowDown'){
          event.preventDefault();event.stopImmediatePropagation();
          open(root);
          if(!panel.hidden)panel.querySelector('a')?.focus();
        }
      },true);
    });
    document.addEventListener('pointerdown',event=>{
      if(!panel.contains(event.target)&&!roots.some(root=>root.contains(event.target)))close();
    },true);
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&!panel.hidden){const previous=activeRoot;close();triggers.get(previous)?.focus();}
    });
    window.addEventListener('resize',()=>{if(activeRoot&&!panel.hidden)position(activeRoot);});
    window.addEventListener('scroll',()=>{if(activeRoot&&!panel.hidden)position(activeRoot);},true);
  }
  function whatsapp(){
    const a=document.createElement('a'); a.id='hydd-live-whatsapp';a.target='_blank';
    a.rel='noopener noreferrer';a.setAttribute('aria-label', {fr:'Contacter HYDD sur WhatsApp',en:'Contact HYDD on WhatsApp',ar:'تواصل مع HYDD عبر واتساب'}[locale]);
    const topic=services[originalPath()]?.[locale]||{fr:'vos prestations',en:'your services',ar:'خدماتكم'}[locale];
    const message=greetings[locale]+topic+'\n'+location.origin+location.pathname;
    a.href='https://wa.me/'+PHONE+'?text='+encodeURIComponent(message);
    a.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8A8.5 8.5 0 0 1 12.5 20a8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 0 1 12.5 3H13a8.5 8.5 0 0 1 8 8v.5z"/></svg>';
    const span=document.createElement('span');span.textContent={fr:'WhatsApp',en:'WhatsApp',ar:'واتساب'}[locale];a.append(span);
    document.body.append(a);
  }
  // Original Squarespace Form Blocks cannot send through Squarespace once off-platform.
  // Bridge only recognizable CONTACT forms to the optional self-hosted API.
  function forms(){
    document.querySelectorAll('.sqs-block-form form, .form-block form, form[data-form-id]').forEach(form=>{
      if(form.dataset.hyddBound)return;
      form.dataset.hyddBound='1';
      form.addEventListener('submit',async event=>{
        if(form.querySelector('input[type="file"]'))return; // never intercept file uploads
        event.preventDefault();
        const get=()=>Array.from(form.querySelectorAll('input,textarea,select')).filter(e=>!e.disabled && e.type!=='hidden');
        const inputs=get();
        const find=(re)=>inputs.find(e=>re.test([e.name,e.id,e.placeholder,e.closest('label')?.textContent,e.type].join(' ')))?.value?.trim()||'';
        const email=find(/email|e-mail|courriel/i);
        const first=find(/first|prénom|prenom/i);
        const last=find(/last|nom\b|surname/i);
        const name=(first+' '+last).trim()||find(/^name|fullname|full.name|^nom\b/i);
        const phone=find(/phone|téléphone|telephone|mobile|tel/i);
        const message=inputs.find(e=>e.tagName==='TEXTAREA')?.value.trim()||find(/message|comment|détails/i);
        const consent=inputs.find(e=>e.type==='checkbox' && /rgpd|consent|privacy|confidential|confidenti|politique/i.test([e.name,e.id,e.closest('label')?.textContent].join(' ')));
        let status=form.querySelector('[data-hydd-form-status]');
        if(!status){status=document.createElement('p');status.setAttribute('role','status');status.dataset.hyddFormStatus='';form.append(status);}
        if(!email||!name||!message){
          status.textContent={fr:'Veuillez renseigner votre nom, email et message.',en:'Please enter your name, email and message.',ar:'يرجى إدخال الاسم والبريد الإلكتروني والرسالة.'}[locale];return;
        }
        if(!consent){
          status.textContent={fr:'Ce formulaire doit inclure une case de confidentialité avant activation. Contactez-nous par WhatsApp ou email.',en:'Privacy acknowledgement must be configured before this form can send. Please use WhatsApp or email.',ar:'يجب إعداد الموافقة على سياسة الخصوصية قبل استخدام النموذج. يرجى التواصل عبر واتساب أو البريد الإلكتروني.'}[locale];return;
        }
        if(!consent.checked){
          status.textContent={fr:'Veuillez accepter la politique de confidentialité.',en:'Please accept the privacy policy.',ar:'يرجى الموافقة على سياسة الخصوصية.'}[locale];return;
        }
        status.textContent={fr:'Envoi en cours…',en:'Sending…',ar:'جارٍ الإرسال…'}[locale];
        try{
          const res=await fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
            name,email,phone,message,language:locale,page:location.origin+location.pathname,
            service:'',date:'',website:'',consent:consent.checked
          })});
          if(!res.ok)throw new Error('Contact service unavailable');
          status.textContent={fr:'Merci, votre demande a été envoyée.',en:'Thank you, your enquiry has been sent.',ar:'شكراً، تم إرسال طلبك.'}[locale];
          form.reset();
        }catch(_){status.textContent={fr:'Service indisponible. Contactez-nous par WhatsApp ou email.',en:'Service unavailable. Please contact us via WhatsApp or email.',ar:'الخدمة غير متاحة. يرجى التواصل عبر واتساب أو البريد الإلكتروني.'}[locale];}
      });
    });
  }
  function start(){
    if(!document.body)return;
    langPicker();
    if(!document.getElementById('hydd-live-whatsapp'))whatsapp();
    forms();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();


/* HYDD_MOBILE_RESPONSIVE_FIX_V1 — original burger remains in place. */
(()=>{
 'use strict';
 function init(){
  const header=document.querySelector('header.header,#header.header');
  if(!header||header.dataset.hyddMobileFallback==='v1')return;
  const menu=header.querySelector('.header-menu');
  const buttons=Array.from(header.querySelectorAll('.header-burger-btn'));
  if(!menu||!buttons.length)return;
  header.dataset.hyddMobileFallback='v1';
  let pending=null;
  const isMobile=()=>window.matchMedia('(max-width: 767px)').matches;
  function close(){
   header.classList.remove('hydd-mobile-menu-fallback-open');
   document.body.classList.remove('hydd-mobile-menu-scroll-lock');
   buttons.forEach(button=>button.setAttribute('aria-expanded','false'));
  }
  buttons.forEach(button=>button.addEventListener('click',()=>{
   if(!isMobile())return;
   if(pending!==null)clearTimeout(pending);
   if(header.classList.contains('hydd-mobile-menu-fallback-open')){close();return}
   pending=setTimeout(()=>{
    pending=null;
    if(!isMobile())return;
    const nativeClass=header.classList.contains('header--menu-open')||
      document.body.classList.contains('header--menu-open');
    const shown=getComputedStyle(menu);
    const nativeVisible=shown.visibility==='visible'&&
      parseFloat(shown.opacity||'1')>0.15&&shown.pointerEvents!=='none';
    if(nativeClass||nativeVisible)return;
    header.classList.add('hydd-mobile-menu-fallback-open');
    document.body.classList.add('hydd-mobile-menu-scroll-lock');
    buttons.forEach(b=>b.setAttribute('aria-expanded','true'));
   },180);
  },false));
  menu.addEventListener('click',event=>{if(event.target.closest('a[href]'))close()});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&header.classList.contains('hydd-mobile-menu-fallback-open'))close()});
  window.addEventListener('resize',()=>{if(!isMobile())close()});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();


/* HYDD_MULTILINGUAL_FORM_BOOT_V1 — shared form assets loaded on any page containing the captured form widget. */
(()=>{
 function load(){
   if(!document.querySelector('.sqs-block-form.form-block'))return;
   if(!document.querySelector('link[data-hydd-multilingual-form]')){
     const css=document.createElement('link');
     css.rel='stylesheet';css.href='/hydd/hydd-form.css';css.dataset.hyddMultilingualForm='v1';document.head.append(css);
   }
   if(!document.querySelector('script[data-hydd-multilingual-form]')){
     const script=document.createElement('script');
     script.src='/hydd/hydd-form.js';script.defer=true;script.dataset.hyddMultilingualForm='v1';
     document.body.append(script);
   }
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load,{once:true});else load();
})();
