$(document).ready(function () {
	// Mobile navigation
	$(".burger").click(function () {
		$(".burger").toggleClass("active");
		$("html").toggleClass("overflow-y-hidden");
	});
	$(".burger").click(function () {
		if ($(".sidebar-panel").is(":visible")) {
			$(".sidebar-panel").removeClass("active").fadeOut(300);
			$("html").removeClass("overflow-y-hidden");
		} else {
			$(".sidebar-panel").addClass("active").fadeIn(300);
			$("html").addClass("overflow-y-hidden");
		}
	});

	// Toggle aside panel
	$(".header__aside-btn").click(function () {
		$(".header__aside, .main-aside").toggleClass("active");
	});

	// Beefup - Navigation subMenu
	$(".navigation-item.subMenu").beefup({
		trigger: ".navigation-link",
		content: ".navigation-submenu",
	});

	// Beefup - Dropdown
	$(".dropdown").beefup({
		trigger: ".dropdown-head",
		content: ".dropdown-body",
		selfClose: true,
		animation: "fade",
	});

	// Beefup - AccessProject
	$(".team-item").beefup({
		trigger: ".team-item__project-toggle",
		content: ".team-item__project-content",
	});

	// Easytabs - Tariff
	$(".tariff-tabs").easytabs({
		tabs: ".tariff-tabs__item",
		defaultTab: ".tariff-tabs__item:nth-child(1)",
		updateHash: false,
	});

	// niceSelect
	$("select").niceSelect();

	// Функция одинаковой высоты блоков в карточке
	function setEqualHeightCardHeader() {
		const cardInfoHeader = document.querySelectorAll(".card-info__header");
		let maxHeightCardHeader = 0;

		cardInfoHeader.forEach((block) => (block.style.height = "auto"));

		cardInfoHeader.forEach((block) => {
			if (block.offsetHeight > maxHeightCardHeader) {
				maxHeightCardHeader = block.offsetHeight;
			}
		});

		cardInfoHeader.forEach((block) => (block.style.height = maxHeightCardHeader + "px"));
	}
	window.addEventListener("load", setEqualHeightCardHeader);
	window.addEventListener("resize", setEqualHeightCardHeader);
});
