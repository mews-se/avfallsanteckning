(function () {
  var NYCKEL = "avfallsanteckning.av";

  // kom ihåg vem som antecknar
  var sparat = "";
  try { sparat = localStorage.getItem(NYCKEL) || ""; } catch (e) {}
  document.querySelectorAll("input.av").forEach(function (f) {
    if (!f.value) f.value = sparat;
    f.addEventListener("change", function () {
      try { localStorage.setItem(NYCKEL, f.value); } catch (e) {}
      document.querySelectorAll("input.av").forEach(function (g) { g.value = f.value; });
    });
  });

  // part vald ur listan eller inskriven
  document.querySelectorAll("select.partval").forEach(function (sel) {
    var mal = sel.dataset.mal;
    function visa() {
      var fri = sel.value === "";
      document.querySelectorAll('.partfri[data-for="' + mal + '"]').forEach(function (d) {
        d.classList.toggle("synlig", fri);
      });
      var val = sel.options[sel.selectedIndex];
      if (mal === "mottagare" && val && val.dataset.adress !== undefined) {
        var adr = document.getElementById("till_adress"), kommun = document.getElementById("till_kommun");
        if (adr && val.dataset.adress) adr.value = val.dataset.adress;
        if (kommun && val.dataset.kommun) kommun.value = val.dataset.kommun;
      }
    }
    sel.addEventListener("change", visa);
    var fri = sel.value === "";
    document.querySelectorAll('.partfri[data-for="' + mal + '"]').forEach(function (d) {
      d.classList.toggle("synlig", fri);
    });
  });

  // kommunen följer av koordinaten tills någon skriver in den för hand
  var koordinat = document.getElementById("fran_koordinat");
  var kommun = document.getElementById("fran_kommun");
  if (koordinat && kommun) {
    koordinat.addEventListener("change", function () {
      if (!koordinat.value.trim() || (kommun.value && !kommun.dataset.auto)) return;
      fetch(koordinat.dataset.url + "?koordinat=" + encodeURIComponent(koordinat.value))
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.namn) { kommun.value = d.namn; kommun.dataset.auto = "1"; } });
    });
    kommun.addEventListener("input", function () { delete kommun.dataset.auto; });
  }

  var sok = document.getElementById("kodsok");
  if (!sok) return;
  var dold = document.getElementById("avfallskod");
  var lista = document.getElementById("kodlista");
  var valt = document.getElementById("kodvalt");
  var alla = document.getElementById("visa_ickefarliga");
  var favoriter = JSON.parse(sok.dataset.favoriter || "[]");
  var koder = [];
  var markerad = -1;

  fetch(sok.dataset.url).then(function (r) { return r.json(); }).then(function (d) { koder = d; });

  function norm(s) { return s.toLowerCase().replace(/\s+/g, " "); }

  function traffar() {
    var q = norm(sok.value.trim());
    var urval = koder.filter(function (k) { return alla.checked || k.farligt; });
    if (!q) {
      return favoriter.map(function (f) {
        return koder.find(function (k) { return k.kod === f; });
      }).filter(function (k) { return k && (alla.checked || k.farligt); });
    }
    var siffror = q.replace(/[^0-9*]/g, "");
    return urval.filter(function (k) {
      if (siffror && /^[0-9 *]+$/.test(q)) return k.kod.replace(/\s/g, "").indexOf(siffror) === 0;
      return norm(k.kod + " " + k.beskrivning + " " + k.grupp).indexOf(q) !== -1;
    }).slice(0, 60);
  }

  function rendera() {
    var t = traffar();
    lista.innerHTML = "";
    markerad = -1;
    if (!sok.value.trim() && t.length) {
      var r = document.createElement("li");
      r.className = "rubrik";
      r.textContent = "Vanliga koder";
      lista.appendChild(r);
    }
    t.forEach(function (k) {
      var li = document.createElement("li");
      var kod = document.createElement("span");
      kod.className = "kod";
      kod.textContent = k.kod;
      var text = document.createElement("span");
      text.textContent = k.beskrivning;
      var grupp = document.createElement("span");
      grupp.className = "grupp";
      grupp.textContent = k.grupp;
      li.appendChild(kod);
      li.appendChild(text);
      li.appendChild(grupp);
      li.addEventListener("mousedown", function (e) { e.preventDefault(); valj(k); });
      lista.appendChild(li);
    });
    if (!t.length) {
      var tom = document.createElement("li");
      tom.className = "rubrik";
      tom.textContent = koder.length ? "Inga träffar" : "Laddar koder …";
      lista.appendChild(tom);
    }
    lista.hidden = false;
  }

  function valj(k) {
    dold.value = k.kod;
    valt.innerHTML = "";
    var b = document.createElement("b");
    b.className = "mono";
    b.textContent = k.kod;
    valt.appendChild(b);
    valt.appendChild(document.createTextNode(" " + k.beskrivning));
    sok.value = "";
    lista.hidden = true;
  }

  sok.addEventListener("input", rendera);
  sok.addEventListener("focus", rendera);
  alla.addEventListener("change", function () { if (!lista.hidden) rendera(); });
  sok.addEventListener("keydown", function (e) {
    var rader = lista.querySelectorAll("li:not(.rubrik)");
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (lista.hidden) rendera();
      markerad = Math.max(0, Math.min(rader.length - 1, markerad + (e.key === "ArrowDown" ? 1 : -1)));
      rader.forEach(function (li, i) { li.classList.toggle("vald", i === markerad); });
      if (rader[markerad]) rader[markerad].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      var li = rader[markerad >= 0 ? markerad : 0];
      if (li) li.dispatchEvent(new MouseEvent("mousedown"));
    } else if (e.key === "Escape") {
      lista.hidden = true;
    }
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".kodvaljare")) lista.hidden = true;
  });
})();
