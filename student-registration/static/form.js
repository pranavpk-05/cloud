const photo=document.getElementById('photo');
let previewUrl;
photo.addEventListener('change',()=>{
  const file=photo.files[0];
  const preview=document.getElementById('preview');
  if(previewUrl) URL.revokeObjectURL(previewUrl);
  preview.hidden=true;
  document.getElementById('upload-icon').hidden=false;
  document.getElementById('file-label').textContent=file?file.name:'Choose a photo';
  photo.setCustomValidity('');
  if(!file) return;
  if(file.size>5*1024*1024 || !['image/jpeg','image/png','image/webp'].includes(file.type)){
    photo.setCustomValidity('Choose a JPG, PNG, or WebP image smaller than 5 MB.');
    document.getElementById('photo-error').textContent=photo.validationMessage;
    photo.reportValidity();return;
  }
  previewUrl=URL.createObjectURL(file);preview.src=previewUrl;preview.hidden=false;
  document.getElementById('upload-icon').hidden=true;
  document.getElementById('photo-error').textContent='Photo selected · Ready to upload';
});
document.getElementById('registration').addEventListener('submit',()=>{
  const button=document.getElementById('submit');button.disabled=true;button.textContent='Saving your registration…';
});
