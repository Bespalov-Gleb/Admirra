<template>
				<section class="main-section">
					<div class="py-4 mb-3">
						<h3 class="heading-3">Проекты</h3>
					</div>
					<div class="row gy-3 mb-5">
						<div class="col-12 col-md">
							<div class="row gy-3">
								<div class="col-auto">
									<select>
										<option>Все</option>
										<option value="1">Some option</option>
										<option value="2">Another option</option>
										<option value="3" disabled>A disabled option</option>
										<option value="4">Potato option</option>
									</select>
								</div>
								<div class="col-auto">
									<select>
										<option>2 недели</option>
										<option value="1">3 недели</option>
										<option value="2">4 недели</option>
										<option value="3">5 недель</option>
									</select>
								</div>
								<div class="col-12 col-sm-auto">
									<div class="input-item">
										<input class="input _search-project" type="text" placeholder="Поиск по проектам, номерам или доменам" />
										<div class="input-icon">
											<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#search"></use></svg>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div class="col-12 col-md-auto">
							<div class="row g-3">
								<div class="col-auto">
									<button class="btn _primary">
										<div class="btn__inner">
											<span class="btn__text">Массовое редактирование</span>
											<div class="btn__icon">
												<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#edit"></use></svg>
											</div>
										</div>
									</button>
								</div>
								<div class="col-auto ms-auto">
									<div class="row">
										<div class="col-auto">
											<button class="btn-ico">
												<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#grid"></use></svg>
											</button>
										</div>
										<div class="col-auto">
											<button class="btn-ico _active">
												<svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#rows"></use></svg>
											</button>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="row gy-4 mb-5">
						<div class="col-12 col-xxl-6">
							<div class="h-100 bg-white radius-base">
								<div class="p-5">
									<div class="row pb-3 mb-4">
										<div class="col">
											<div class="d-flex">
												<div class="avatar-40x40 align-self-center">
													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
												</div>
												<div class="ps-4 align-self-center">
													<h4 class="mb-1 text-15 gray">Дейтелинг Иркутск</h4>
													<p class="gray56">Описание проекта краткое</p>
												</div>
											</div>
										</div>
										<div class="col-auto">
											<a class="circle-btn" href="#">
												<svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
											</a>
										</div>
									</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Показы</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">120,302</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#cursore"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Клики</h4>
														<p class="text-12 gray56">Все переходы</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama-circle"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPC</h4>
														<p class="text-12 gray56">Стоимость клика</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">9,63&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg class="_wallet"><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Расходы</h4>
														<p class="text-12 gray56">За период</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">90,190&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#calendar"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Лиды</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">130&nbsp;шт.</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#ok"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPA</h4>
														<p class="text-12 gray56">Стоимость лида</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
								<hr class="hr-line" />
								<div class="p-5">
									<div class="gray mb-3">Актуальный баланс в ЛК:</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-orangelight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/yandex-direct.png" alt="yandex direct" />
													<div class="px-3 c71663e">Yandex Direct</div>
													<div class="badge-white c71663e">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-oceanlight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/vk-ads.png" alt="vk" />
													<div class="px-3 c254b78">ВК&nbsp;Ads Manager</div>
													<div class="badge-white c254b78">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-roselight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/target.png" alt="vk" />
													<div class="px-3 c662529">Шаблон канала</div>
													<div class="badge-white c662529">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div class="col-12 col-xxl-6">
							<div class="h-100 bg-white radius-base">
								<div class="p-5">
									<div class="row pb-3 mb-4">
										<div class="col">
											<div class="d-flex">
												<div class="avatar-40x40 align-self-center">
													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
												</div>
												<div class="ps-4 align-self-center">
													<h4 class="mb-1 text-15 gray">Дейтелинг Иркутск</h4>
													<p class="gray56">Описание проекта краткое</p>
												</div>
											</div>
										</div>
										<div class="col-auto">
											<a class="circle-btn" href="#">
												<svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
											</a>
										</div>
									</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Показы</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">120,302</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#cursore"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Клики</h4>
														<p class="text-12 gray56">Все переходы</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama-circle"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPC</h4>
														<p class="text-12 gray56">Стоимость клика</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">9,63&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg class="_wallet"><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Расходы</h4>
														<p class="text-12 gray56">За период</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">90,190&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#calendar"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Лиды</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">130&nbsp;шт.</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#ok"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPA</h4>
														<p class="text-12 gray56">Стоимость лида</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
								<hr class="hr-line" />
								<div class="p-5">
									<div class="gray mb-3">Актуальный баланс в ЛК:</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-orangelight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/yandex-direct.png" alt="yandex direct" />
													<div class="px-3 c71663e">Yandex Direct</div>
													<div class="badge-white c71663e">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-oceanlight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/vk-ads.png" alt="vk" />
													<div class="px-3 c254b78">ВК&nbsp;Ads Manager</div>
													<div class="badge-white c254b78">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-roselight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/target.png" alt="vk" />
													<div class="px-3 c662529">Шаблон канала</div>
													<div class="badge-white c662529">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div class="col-12 col-xxl-6">
							<div class="h-100 bg-white radius-base">
								<div class="p-5">
									<div class="row pb-3 mb-4">
										<div class="col">
											<div class="d-flex">
												<div class="avatar-40x40 align-self-center">
													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
												</div>
												<div class="ps-4 align-self-center">
													<h4 class="mb-1 text-15 gray">Дейтелинг Иркутск</h4>
													<p class="gray56">Описание проекта краткое</p>
												</div>
											</div>
										</div>
										<div class="col-auto">
											<a class="circle-btn" href="#">
												<svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
											</a>
										</div>
									</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Показы</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">120,302</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#cursore"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Клики</h4>
														<p class="text-12 gray56">Все переходы</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama-circle"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPC</h4>
														<p class="text-12 gray56">Стоимость клика</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">9,63&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg class="_wallet"><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Расходы</h4>
														<p class="text-12 gray56">За период</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">90,190&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#calendar"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Лиды</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">130&nbsp;шт.</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#ok"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPA</h4>
														<p class="text-12 gray56">Стоимость лида</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
								<hr class="hr-line" />
								<div class="p-5">
									<div class="gray mb-3">Актуальный баланс в ЛК:</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-orangelight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/yandex-direct.png" alt="yandex direct" />
													<div class="px-3 c71663e">Yandex Direct</div>
													<div class="badge-white c71663e">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-oceanlight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/vk-ads.png" alt="vk" />
													<div class="px-3 c254b78">ВК&nbsp;Ads Manager</div>
													<div class="badge-white c254b78">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-roselight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/target.png" alt="vk" />
													<div class="px-3 c662529">Шаблон канала</div>
													<div class="badge-white c662529">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div class="col-12 col-xxl-6">
							<div class="h-100 bg-white radius-base">
								<div class="p-5">
									<div class="row pb-3 mb-4">
										<div class="col">
											<div class="d-flex">
												<div class="avatar-40x40 align-self-center">
													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
												</div>
												<div class="ps-4 align-self-center">
													<h4 class="mb-1 text-15 gray">Дейтелинг Иркутск</h4>
													<p class="gray56">Описание проекта краткое</p>
												</div>
											</div>
										</div>
										<div class="col-auto">
											<a class="circle-btn" href="#">
												<svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
											</a>
										</div>
									</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Показы</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">120,302</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#cursore"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Клики</h4>
														<p class="text-12 gray56">Все переходы</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#diagrama-circle"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPC</h4>
														<p class="text-12 gray56">Стоимость клика</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">9,63&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg class="_wallet"><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Расходы</h4>
														<p class="text-12 gray56">За период</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">90,190&nbsp;₽</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#calendar"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">Лиды</h4>
														<p class="text-12 gray56">По всем каналам</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">130&nbsp;шт.</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
												<div class="d-flex pb-2 mb-4">
													<div class="iconbox">
														<svg><use href="/admirra/img/svg/sprite.svg#ok"></use></svg>
													</div>
													<div class="ps-3 align-self-center">
														<h4 class="mb-1 gray">CPA</h4>
														<p class="text-12 gray56">Стоимость лида</p>
													</div>
												</div>
												<div class="d-flex align-items-center mt-auto">
													<b class="text-20 me-3">967</b>
													<div class="badge _success">
														<svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
														+15.6%
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
								<hr class="hr-line" />
								<div class="p-5">
									<div class="gray mb-3">Актуальный баланс в ЛК:</div>
									<div class="row g-4">
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-orangelight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/yandex-direct.png" alt="yandex direct" />
													<div class="px-3 c71663e">Yandex Direct</div>
													<div class="badge-white c71663e">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-oceanlight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/vk-ads.png" alt="vk" />
													<div class="px-3 c254b78">ВК&nbsp;Ads Manager</div>
													<div class="badge-white c254b78">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
										<div class="col-12 col-sm-6 col-md-4">
											<div class="h-100 bg-roselight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/target.png" alt="vk" />
													<div class="px-3 c662529">Шаблон канала</div>
													<div class="badge-white c662529">10&nbsp;200₽</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</section>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'

onMounted(() => {
  nextTick(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect();
      window.jQuery('.dropdown').beefup({
        trigger: '.dropdown-head',
        content: '.dropdown-body',
        selfClose: true,
        animation: 'fade',
      });
      if (window.jQuery('.tariff-tabs').length) {
        window.jQuery('.tariff-tabs').easytabs({
          tabs: '.tariff-tabs__item',
          defaultTab: '.tariff-tabs__item:nth-child(1)',
          updateHash: false,
        });
      }
    }
  });
})
</script>
