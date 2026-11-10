// Validasi form customer di sisi klien + konfirmasi aksi nonaktif/hapus.
document.querySelectorAll("form[data-customer]").forEach(function (form) {
  form.addEventListener("submit", function (event) {
    var fields = [
      { input: form.elements.kode, message: "Kode customer wajib diisi." },
      { input: form.elements.nama, message: "Nama customer wajib diisi." },
    ];
    for (var i = 0; i < fields.length; i++) {
      var input = fields[i].input;
      input.value = input.value.trim();
      if (!input.value) {
        event.preventDefault();
        alert(fields[i].message);
        input.focus();
        return;
      }
    }
  });
});

document.querySelectorAll("form[data-confirm]").forEach(function (form) {
  form.addEventListener("submit", function (event) {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  });
});
