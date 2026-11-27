const photo = document.querySelector('[name="photo"]');
photo.addEventListener('change', () => {
  const file = photo.files[0];
  const tooLarge = file && file.size > 3 * 1024 * 1024;
  photo.setCustomValidity(tooLarge ? '3 MB以内の画像を選んでください。' : '');
  document.querySelector('#file-note').textContent = tooLarge ? photo.validationMessage : (file?.name || '');
});
