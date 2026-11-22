// EduCore on Frappe's website pages. The look is in educore-web.css; this adds the hero column beside the
// login card, puts the logo-on-dark in the card, and shows the brand's icon in place of Frappe's and
// ERPNext's logos on the /apps screen. The text and images come from window.educore_branding, which
// educore_theme.branding.website_context() puts in the page (EduCore Branding, or EduCore's defaults).
(function () {
	const brand = window.educore_branding || {};
	const STOCK_LOGOS = [
		"/erpnext/images/erpnext-logo.svg",
		"/frappe/images/frappe-framework-logo.svg",
		"/frappe/images/frappe-framework-logo.png",
		"/frappe/images/frappe-logo.png",
	];

	const swapStockLogos = () => {
		if (!brand.mark) return;
		const selector = STOCK_LOGOS.map((path) => `img[src$="${path}"]`).join(", ");
		document.querySelectorAll(selector).forEach((img) => {
			img.src = brand.mark;
		});
	};

	const el = (tag, className, text) => {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text) node.textContent = text;
		return node;
	};

	const loginHero = () => {
		if (document.body.dataset.path !== "login") return;
		const login = document.querySelector("section.for-login");
		if (!login || document.querySelector(".edu-login-hero")) return;

		const hero = el("div", "edu-login-hero");
		const eyebrow = el("p", "edu-login-brand", `${brand.institution_name || "EduCore"} · `);
		eyebrow.appendChild(el("span", "edu-gradient-brand", brand.login_subtitle || ""));
		hero.appendChild(eyebrow);

		const h1 = el("h1", "edu-login-heading", `${brand.login_heading || ""} `);
		h1.appendChild(el("span", "edu-gradient-accent", brand.login_heading_accent || ""));
		hero.appendChild(h1);
		if (brand.login_text) hero.appendChild(el("p", "edu-login-text", brand.login_text));

		if (brand.facts && brand.facts.length) {
			const facts = el("dl", "edu-login-facts");
			brand.facts.forEach(([title, caption]) => {
				const fact = el("div");
				fact.appendChild(el("dt", null, title));
				fact.appendChild(el("dd", null, caption));
				facts.appendChild(fact);
			});
			hero.appendChild(facts);
		}

		const wrapper = login.parentElement;
		wrapper.classList.add("edu-login-layout");
		wrapper.insertBefore(hero, wrapper.firstChild);

		if (brand.logo_on_dark) {
			document.querySelectorAll(".page-card .app-logo").forEach((img) => {
				img.src = brand.logo_on_dark;
				img.alt = brand.institution_name || "EduCore";
			});
		}
		const head = login.querySelector(".page-card-head-text") || login.querySelector(".page-card-head");
		if (head) {
			const title = head.querySelector("h4");
			const subtitle = head.querySelector(".page-card-subtitle");
			if (title) title.textContent = "Sign in";
			if (subtitle) subtitle.textContent = brand.institution_name || "EduCore";
		}
	};

	const run = () => {
		loginHero();
		swapStockLogos();
	};
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
	else run();
	// the /apps screen draws its tiles after load
	if (window.location.pathname.startsWith("/apps")) {
		new MutationObserver(swapStockLogos).observe(document.body, { childList: true, subtree: true });
	}
})();
