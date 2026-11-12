/* HYDD_MULTILINGUAL_FORM_V1 — replaces language-locked Squarespace forms visually; never submits to Squarespace. */
(()=>{'use strict';
 const code=(document.documentElement.lang||location.pathname.split('/').filter(Boolean)[0]||'fr').toLowerCase().slice(0,2);
 const lang=['en','ar'].includes(code)?code:'fr';
 const lex={
  fr:{first:'Prénom',last:'Nom de famille',email:'Adresse e-mail',message:'Votre message',consent:'J’accepte que HYDD utilise ces informations pour répondre à ma demande.',send:'Envoyer',sending:'Envoi en cours…',missing:'Veuillez renseigner votre prénom, nom, adresse e-mail et message (8 caractères minimum).',badEmail:'Veuillez saisir une adresse e-mail valide.',privacy:'Veuillez accepter le traitement de votre demande.',success:'Merci, votre message a été envoyé.',fail:'Le message n’a pas été envoyé. Le service de messagerie est indisponible. Vous pouvez contacter HYDD sur WhatsApp.',wa:'Contacter HYDD sur WhatsApp'},
  en:{first:'First name',last:'Last name',email:'Email address',message:'Your message',consent:'I agree that HYDD may use these details to respond to my enquiry.',send:'Send',sending:'Sending…',missing:'Please enter your first name, last name, email and message (at least 8 characters).',badEmail:'Please enter a valid email address.',privacy:'Please agree to the handling of your enquiry.',success:'Thank you, your message has been sent.',fail:'Your message was not sent. The email service is unavailable. You can contact HYDD through WhatsApp.',wa:'Contact HYDD on WhatsApp'},
  ar:{first:'الاسم الأول',last:'اسم العائلة',email:'البريد الإلكتروني',message:'رسالتك',consent:'أوافق على استخدام HYDD لهذه البيانات للرد على استفساري.',send:'إرسال',sending:'جارٍ الإرسال…',missing:'يرجى إدخال الاسم الأول واسم العائلة والبريد الإلكتروني ورسالة لا تقل عن 8 أحرف.',badEmail:'يرجى إدخال بريد إلكتروني صحيح.',privacy:'يرجى الموافقة على معالجة استفسارك.',success:'شكراً لك، تم إرسال رسالتك.',fail:'لم تُرسل رسالتك. خدمة البريد الإلكتروني غير متاحة حالياً. يمكنك التواصل مع HYDD عبر واتساب.',wa:'تواصل مع HYDD عبر واتساب'}
 },w=lex[lang];
 function input(label,name,type,id,extra){
  const l=document.createElement('label');l.setAttribute('for',id);
  const heading=document.createElement('span');heading.textContent=label+' *';l.append(heading);
  const el=document.createElement(type==='textarea'?'textarea':'input');
  if(type!=='textarea')el.type=type;else{el.rows=5;el.maxLength=4000;}
  el.name=name;el.id=id;el.required=true;
  if(extra)Object.entries(extra).forEach(([key,val])=>el.setAttribute(key,val));
  l.append(el);return l;
 }
 function mount(block,i){
  if(block.querySelector('.hydd-contact-form-host'))return;
  const original=block.querySelector('.form-wrapper');
  if(!original)return;
  original.classList.add('hydd-original-form-hidden');original.setAttribute('aria-hidden','true');
  const host=document.createElement('div');
  host.className='hydd-contact-form-host';host.lang=lang;host.dir=lang==='ar'?'rtl':'ltr';
  const form=document.createElement('form');
  form.className='hydd-independent-contact-form';form.noValidate=true;form.dataset.hyddBound='1';
  const row=document.createElement('div');row.className='hydd-contact-form-row';
  row.append(input(w.first,'first_name','text','hydd-first-'+i,{'autocomplete':'given-name','maxlength':'60'}));
  row.append(input(w.last,'last_name','text','hydd-last-'+i,{'autocomplete':'family-name','maxlength':'60'}));
  form.append(row);
  form.append(input(w.email,'email','email','hydd-email-'+i,{'autocomplete':'email','maxlength':'254','dir':'ltr'}));
  form.append(input(w.message,'message','textarea','hydd-message-'+i));
  const spam=document.createElement('div');spam.className='hydd-form-antispam';spam.setAttribute('aria-hidden','true');
  const honeypot=document.createElement('input');honeypot.name='website';honeypot.tabIndex=-1;honeypot.autocomplete='off';spam.append(honeypot);form.append(spam);
  const consentLabel=document.createElement('label');consentLabel.className='hydd-contact-consent';
  const check=document.createElement('input');check.type='checkbox';check.name='privacy';check.required=true;
  const consentText=document.createElement('span');consentText.textContent=w.consent;
  consentLabel.append(check,consentText);form.append(consentLabel);
  const actions=document.createElement('div');actions.className='hydd-contact-action';
  const submit=document.createElement('button');submit.type='submit';submit.textContent=w.send;actions.append(submit);form.append(actions);
  const status=document.createElement('div');status.className='hydd-contact-status';
  status.setAttribute('role','status');status.setAttribute('aria-live','polite');form.append(status);
  host.append(form);original.insertAdjacentElement('afterend',host);
  let busy=false;
  form.addEventListener('submit',async event=>{
   event.preventDefault();event.stopPropagation();if(busy)return;
   status.replaceChildren();
   const first=form.elements.first_name.value.trim(),last=form.elements.last_name.value.trim();
   const email=form.elements.email.value.trim(),message=form.elements.message.value.trim();
   if(!first||!last||!email||message.length<8){status.textContent=w.missing;return;}
   if(!form.elements.email.checkValidity()){status.textContent=w.badEmail;return;}
   if(!form.elements.privacy.checked){status.textContent=w.privacy;return;}
   busy=true;submit.disabled=true;submit.textContent=w.sending;status.textContent=w.sending;
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
   try{
    const response=await fetch('/api/contact',{method:'POST',credentials:'same-origin',signal:controller.signal,
      headers:{'Content-Type':'application/json'},body:JSON.stringify({
       name:(first+' '+last).slice(0,120),email,phone:'',message,service:'',date:'',
       language:lang,consent:true,website:form.elements.website.value,page:location.origin+location.pathname
      })});
    if(!response.ok)throw Error('contact_unavailable');
    form.reset();status.textContent=w.success;
   }catch(_){
    status.textContent=w.fail+' ';
    const a=document.createElement('a');a.textContent=w.wa;a.target='_blank';a.rel='noopener noreferrer';
    a.href='https://wa.me/33765849546?text='+encodeURIComponent({fr:'Bonjour HYDD, je souhaite vous contacter.',en:'Hello HYDD, I would like to contact you.',ar:'مرحباً HYDD، أود التواصل معكم.'}[lang]);
    status.append(a);
   }finally{clearTimeout(timer);busy=false;submit.disabled=false;submit.textContent=w.send;}
  });
 }
 function init(){document.querySelectorAll('.sqs-block-form.form-block').forEach(mount);}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();