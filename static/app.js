// Validasi form customer di sisi klien + konfirmasi aksi nonaktif.
document.querySelectorAll("form[data-customer]").forEach(function (form) {
  form.addEventListener("submit", function (event) {
    var input = form.elements.name;
    input.value = input.value.trim();
    if (!input.value) {
      event.preventDefault();
      alert("Nama customer wajib diisi.");
      input.focus();
    }
  });
});

document.querySelectorAll("form[data-confirm]").forEach(function (form) {
  form.addEventListener("submit", function (event) {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  });
});
