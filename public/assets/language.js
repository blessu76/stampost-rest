(() => {
  "use strict";

  const select = document.getElementById("ipe-lang-select");
  const language = window.IpeLang;
  if (!select || !language) return;

  function remember(code) {
    try {
      localStorage.setItem("ipe_lang", code);
    } catch {
      // Navigation also works with storage disabled.
    }
  }

  function destination(option) {
    const url = new URL(option.value, location.origin);
    url.search = location.search;
    url.searchParams.delete("lang");
    url.hash = location.hash;
    return url;
  }

  // Use the kit's markup and options, while removing a stale explicit query.
  select.addEventListener("change", (event) => {
    event.stopImmediatePropagation();
    const option = select.selectedOptions[0];
    remember(option.lang);
    location.assign(destination(option));
  }, true);

  if (!document.documentElement.hasAttribute("data-language-entry")) return;
  if (/bot|crawl|spider|slurp|bingpreview|lighthouse|pagespeed|preview/i.test(navigator.userAgent)) return;

  const options = Array.from(select.options);
  const params = new URLSearchParams(location.search);
  const explicit = language.pick([params.get("lang")]);
  const explicitEnglish = /^en(?:[-_]|$)/i.test((params.get("lang") || "").trim());
  const validExplicit = explicit !== "en" || explicitEnglish;
  if (validExplicit) remember(explicit);
  const detected = language.pick(navigator.languages?.length ? navigator.languages : [navigator.language]);
  const selected = validExplicit ? explicit : (params.has("lang") ? detected : (language.stored() || detected));
  const option = options.find((item) => item.lang === selected);
  if (option && option.lang !== select.selectedOptions[0].lang) {
    location.replace(destination(option));
  }
})();
