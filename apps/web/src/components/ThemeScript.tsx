const SCRIPT = `(function(){try{var t=localStorage.getItem("triavoz-theme");if(t==="light"||t==="dark"){document.documentElement.dataset.theme=t;}}catch(e){}})();`;

/** Runs before paint so the first frame already has the chosen theme (no flash). */
export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: SCRIPT }} />;
}
