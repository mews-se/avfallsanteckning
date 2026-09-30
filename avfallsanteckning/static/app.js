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

  // avfallsrader med varsin kodväljare
  var rader = document.getElementById("avfallsrader");
  if (!rader) return;
  var alla = document.getElementById("visa_ickefarliga");
  var favoriter = JSON.parse(rader.dataset.favoriter || "[]");
  var koder = [];
  var nasta = 1;
  rader.querySelectorAll(".avfallsrad").forEach(function (r) { nasta = Math.max(nasta, Number(r.dataset.n) + 1); });

  fetch(rader.dataset.url).then(function (r) { return r.json(); }).then(function (d) { koder = d; });

  function norm(s) { return s.toLowerCase().replace(/\s+/g, " "); }

  function kodvaljare(rad) {
    var sok = rad.querySelector(".kodsok");
    var dold = rad.querySelector("input[type=hidden]");
    var lista = rad.querySelector(".kodlista");
    var valt = rad.querySelector(".kodvalt");
    var markerad = -1;

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
      var vikt = rad.querySelector("input[name^=vikt_kg]");
      if (vikt && !vikt.value) vikt.focus();
    }

    sok.addEventListener("input", rendera);
    sok.addEventListener("focus", rendera);
    alla.addEventListener("change", function () { if (!lista.hidden) rendera(); });
    sok.addEventListener("keydown", function (e) {
      var val = lista.querySelectorAll("li:not(.rubrik)");
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (lista.hidden) rendera();
        markerad = Math.max(0, Math.min(val.length - 1, markerad + (e.key === "ArrowDown" ? 1 : -1)));
        val.forEach(function (li, i) { li.classList.toggle("vald", i === markerad); });
        if (val[markerad]) val[markerad].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        e.preventDefault();
        var li = val[markerad >= 0 ? markerad : 0];
        if (li) li.dispatchEvent(new MouseEvent("mousedown"));
      } else if (e.key === "Escape") {
        lista.hidden = true;
      }
    });
  }

  function numrera() {
    rader.querySelectorAll(".avfallsrad").forEach(function (r, i) { r.querySelector(".nr").textContent = i + 1; });
  }

  function koppla(rad) {
    kodvaljare(rad);
    rad.querySelector(".ta_bort").addEventListener("click", function () {
      if (rader.querySelectorAll(".avfallsrad").length > 1) {
        rad.remove();
      } else {
        rad.querySelector("input[type=hidden]").value = "";
        rad.querySelector(".kodvalt").innerHTML = '<span class="tom">Ingen kod vald</span>';
        rad.querySelector("input[name^=vikt_kg]").value = "";
        rad.querySelector("input[type=checkbox]").checked = false;
      }
      numrera();
    });
  }

  rader.querySelectorAll(".avfallsrad").forEach(koppla);
  var mall = document.getElementById("avfallsrad-mall");
  var lagg = document.getElementById("lagg_till_avfall");
  if (lagg) lagg.addEventListener("click", function () {
    var div = document.createElement("div");
    div.innerHTML = mall.innerHTML.replace(/__N__/g, nasta++);
    var rad = div.firstElementChild;
    rader.appendChild(rad);
    koppla(rad);
    numrera();
    rad.querySelector(".kodsok").focus();
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".kodvaljare")) {
      rader.querySelectorAll(".kodlista").forEach(function (l) { l.hidden = true; });
    }
  });
})();
