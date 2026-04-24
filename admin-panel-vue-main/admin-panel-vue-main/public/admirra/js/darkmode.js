const body = document.querySelector("body");
const btn = document.querySelector(".dropdown-menu-item._darkmode");
const icon = document.querySelector(".darkmode-btn__indicator");

//to save the dark mode use the object "local storage".

//function that stores the value true if the dark mode is activated or false if it's not.
function store(value) {
	localStorage.setItem("darkmode", value);
}

//function that indicates if the "darkmode" property exists. It loads the page as we had left it.
function load() {
	const darkmode = localStorage.getItem("darkmode");

	//if the dark mode was never activated
	if (!darkmode) {
		store(false);
		icon.classList.add("darkmode-moon");
	} else if (darkmode == "true") {
		//if the dark mode is activated
		body.classList.add("darkmode");
		icon.classList.add("darkmode-sun");
	} else if (darkmode == "false") {
		//if the dark mode exists but is disabled
		icon.classList.add("darkmode-moon");
	}
}

load();

btn.addEventListener("click", () => {
	body.classList.toggle("darkmode");
	icon.classList.add("animated");

	//save true or false
	store(body.classList.contains("darkmode"));

	if (body.classList.contains("darkmode")) {
		icon.classList.remove("darkmode-moon");
		icon.classList.add("darkmode-sun");
	} else {
		icon.classList.remove("darkmode-sun");
		icon.classList.add("darkmode-moon");
	}

	setTimeout(() => {
		icon.classList.remove("animated");
	}, 500);
});
