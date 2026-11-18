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

// tombol "+ Tambah consumable": salin baris terakhir lalu kosongkan isinya
document.querySelectorAll("[data-add-row]").forEach(function (button) {
  button.addEventListener("click", function () {
    var body = document.querySelector(button.dataset.addRow);
    var row = body.lastElementChild;
    if (!row) return;
    row = row.cloneNode(true);
    row.querySelectorAll("select").forEach(function (s) { s.selectedIndex = 0; });
    row.querySelectorAll("input").forEach(function (i) { i.value = 0; });
    body.appendChild(row);
  });
});

// bentuk Rod: diameter aktif, tebal/lebar dikunci. Block/Plate: sebaliknya.
(function () {
  var shape = document.getElementById("shape");
  if (!shape) return;
  var kunci = function () {
    var rod = shape.value.indexOf("Rod") === 0;
    document.getElementById("diameter").disabled = !rod;
    document.getElementById("tebal").disabled = rod;
    document.getElementById("lebar").disabled = rod;
  };
  shape.addEventListener("change", kunci);
  kunci();
})();
