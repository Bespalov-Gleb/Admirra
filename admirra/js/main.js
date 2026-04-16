$(document).ready(function () {
	$(".burger").click(function () {
		$(".burger").toggleClass("active");
		$("html").toggleClass("overflow-y-hidden");
	});
	$(".mobile-nav__close, .mobile-nav__menu a").click(function () {
		$(".mobile-nav").fadeOut(300);
		$("html").removeClass("overflow-y-hidden");
		$(".burger").removeClass("active");
	});
	$(".burger").click(function () {
		if ($(".mobile-nav").is(":visible")) {
			$(".mobile-nav").fadeOut(300);
			$("html").removeClass("overflow-y-hidden");
		} else {
			$(".mobile-nav").fadeIn(300);
			$("html").addClass("overflow-y-hidden");
		}
	});

	document.querySelectorAll(".menu-scroll a").forEach((anchor) => {
		anchor.addEventListener("click", function (e) {
			e.preventDefault();
			document.querySelector(this.getAttribute("href")).scrollIntoView({
				behavior: "smooth",
			});
		});
	});

	new Swiper(".integrations-slider", {
		slidesPerView: "auto",
		speed: 5000,
		spaceBetween: 15,
		autoplay: {
			delay: 0,
			enabled: true,
		},
		effect: "linear",
		freeMode: true,
		loop: true,
	});

	$(".faq-item").beefup({
		openSingle: true,
		trigger: ".faq-head",
		content: ".faq-body",
	});

	$(".tariff-tabs").easytabs({
		tabs: ".tariff-tabs__item",
		defaultTab: ".tariff-tabs__item:nth-child(1)",
		updateHash: false,
	});
});
