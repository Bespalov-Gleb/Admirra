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
					<div class="bg-white radius-base py-5 mb-5">
						<div class="table-container">
							<table>
								<thead>
									<tr class="gray56">
										<th class="bb-light px-3 pb-3">
											<div class="ps-4">
												<label class="choise-checkbox">
													<input class="choise-checkbox__input" type="checkbox" />
													<span class="choise-checkbox__box">
														<svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
													</span>
												</label>
											</div>
										</th>
										<th class="bb-light px-3 pb-3">Проект</th>
										<th class="bb-light px-3 pb-3">Интеграции</th>
										<th class="bb-light px-3 pb-3">Показы</th>
										<th class="bb-light px-3 pb-3">Клики</th>
										<th class="bb-light px-3 pb-3">Расходы</th>
										<th class="bb-light px-3 pb-3">Лиды</th>
										<th class="bb-light px-3 pb-3">CPC</th>
										<th class="bb-light px-3 pb-3">CPA</th>
										<th class="bb-light px-3 pb-3">Актуальный баланс&nbsp;в&nbsp;ЛК:</th>
										<th class="bb-light px-3 pb-3">Статус</th>
										<th class="bb-light px-3 pb-3">Дата&nbsp;создания</th>
										<th class="bb-light px-3 pb-3">Действия</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="project in projects" :key="project.id">
										<td class="bb-light px-3 py-5">
											<div class="ps-4">
												<label class="choise-checkbox">
													<input class="choise-checkbox__input" type="checkbox" />
													<span class="choise-checkbox__box">
														<svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
													</span>
												</label>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="d-flex">
												<div class="avatar-30x30 align-self-center">
													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
												</div>
												<div class="ps-4 align-self-center">
													<h4 class="mb-1 gray">{{ project.title }}</h4>
													<p class="text-11 gray56">ID:&nbsp;{{ project.id }}</p>
												</div>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="d-flex">
												<img v-if="project.channels.includes('YANDEX_DIRECT')" class="me-2" width="22" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" />
												<img v-if="project.channels.includes('VK_ADS')" class="me-2" width="22" src="/admirra/img/icons/vk-ads.png" alt="VK" />
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">{{ project.impressions }}</div>
											<div class="badge _sm _success" v-if="project.trend > 0">
												<span class="weight-600">+{{ Number(project.trend).toFixed(1) }}%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">{{ project.clicks }}</div>
											<div class="badge _sm _success" v-if="project.trend > 0">
												<span class="weight-600">+{{ Number(project.trend).toFixed(1) }}%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2"><b>{{ Number(project.expenses).toLocaleString() }}&nbsp;₽</b></div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">{{ project.leads }}</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">{{ Number(project.cpc).toFixed(2) }}</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">{{ Number(project.cpa).toFixed(2) }}</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="h-100 bg-orangelight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<div class="px-3 c71663e">Баланс</div>
													<div class="badge-white c71663e">{{ project.budgetRemaining }}₽</div>
												</div>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="badge _success">
												<span class="weight-600">{{ project.status }}</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15">{{ project.createdAt }}</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="dropdown">
												<button class="dropdown-head _no-style">
													<div class="action-btn-ui">
														<svg><use href="/admirra/img/svg/sprite.svg#dotts"></use></svg>
													</div>
												</button>
												<div class="dropdown-body _action _right">
													<div class="dropdown-block">
														<div class="py-3">
															<router-link :to="'/project-card?id=' + project.id" class="dropdown-menu-item">
																<div class="dropdown-menu-item__icon">
																	<svg class="_sm"><use href="/admirra/img/svg/sprite.svg#eye"></use></svg>
																</div>
																<span class="pe-3">Просмотр</span>
															</router-link>
															<button class="dropdown-menu-item">
																<div class="dropdown-menu-item__icon">
																	<svg class="_stroke _lg"><use href="/admirra/img/svg/sprite.svg#pen"></use></svg>
																</div>
																<span class="pe-3">Редактировать</span>
															</button>
															<button @click.prevent="deleteProject(project.id)" class="dropdown-menu-item _danger">
																<div class="dropdown-menu-item__icon">
																	<svg><use href="/admirra/img/svg/sprite.svg#delete"></use></svg>
																</div>
																<span class="pe-3">Удалить</span>
															</button>
														</div>
													</div>
												</div>
											</div>
										</td>
									</tr>
									<tr>
										<td class="bb-light px-3 py-5">
											<div class="ps-4">
												<label class="choise-checkbox">
													<input class="choise-checkbox__input" type="checkbox" checked />
													<span class="choise-checkbox__box">
														<svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
													</span>
												</label>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="d-flex">
												<div class="avatar-30x30 align-self-center">
													<img class="img-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="#" />
												</div>
												<div class="ps-4 align-self-center">
													<h4 class="mb-1 gray">Дейтелинг Иркутск</h4>
													<p class="text-11 gray56">ID:&nbsp;098409843080980</p>
												</div>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="d-flex">
												<img class="me-2" width="22" src="/admirra/img/icons/yandex-direct.png" alt="#" />
												<img class="me-2" width="22" src="/admirra/img/icons/vk-ads.png" alt="#" />
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">1205</div>
											<div class="badge _sm _success">
												<span class="weight-600">+15.6%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">1205</div>
											<div class="badge _sm _success">
												<span class="weight-600">+15.6%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2"><b>90,190&nbsp;₽</b></div>
											<div class="badge _sm _success">
												<span class="weight-600">+15.6%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">67</div>
											<div class="badge _sm _success">
												<span class="weight-600">+15.6%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">67</div>
											<div class="badge _sm _success">
												<span class="weight-600">+15.6%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15 mb-2">67</div>
											<div class="badge _sm _success">
												<span class="weight-600">+15.6%</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="h-100 bg-orangelight radius p-3">
												<div class="h-100 d-flex align-items-center justify-content-center">
													<img width="18" src="/admirra/img/icons/yandex-direct.png" alt="yandex direct" />
													<div class="px-3 c71663e">Yandex&nbsp;Direct</div>
													<div class="badge-white c71663e">10&nbsp;200₽</div>
												</div>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="badge _success">
												<span class="weight-600">Активен</span>
											</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="text-15">09.03.2026</div>
										</td>
										<td class="bb-light px-3 py-5">
											<div class="dropdown">
												<button class="dropdown-head _no-style">
													<div class="action-btn-ui">
														<svg><use href="/admirra/img/svg/sprite.svg#dotts"></use></svg>
													</div>
												</button>
												<div class="dropdown-body _action _right">
													<div class="dropdown-block">
														<div class="py-3">
															<router-link to="/project-card" class="dropdown-menu-item">
																<div class="dropdown-menu-item__icon">
																	<svg class="_sm"><use href="/admirra/img/svg/sprite.svg#eye"></use></svg>
																</div>
																<span class="pe-3">Просмотр</span>
															</router-link>
															<button class="dropdown-menu-item">
																<div class="dropdown-menu-item__icon">
																	<svg class="_stroke _lg"><use href="/admirra/img/svg/sprite.svg#pen"></use></svg>
																</div>
																<span class="pe-3">Редактировать</span>
															</button>
															<button class="dropdown-menu-item _danger">
																<div class="dropdown-menu-item__icon">
																	<svg><use href="/admirra/img/svg/sprite.svg#delete"></use></svg>
																</div>
																<span class="pe-3">Удалить</span>
															</button>
														</div>
													</div>
												</div>
											</div>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
						<div class="row pt-5 px-5 align-items-end">
							<div class="col col-sm-4">
								<div class="row gy-2 align-items-center">
									<div class="col-12">
										<div class="gray weight-500">Элементов на&nbsp;странице:</div>
									</div>
									<div class="col-auto">
										<select class="select-outline wide _sm _dropdown-bottom">
											<option>10</option>
											<option value="1">20</option>
											<option value="2">30</option>
										</select>
									</div>
								</div>
							</div>
							<div class="col-12 col-sm-4 order-1 order-sm-0">
								<div class="py-4 gray weight-500 text-center">1-3 из 3</div>
							</div>
							<div class="col-auto col-sm-4 d-flex">
								<div class="ms-auto">
									<a class="btn-nav" href="#">
										<svg><use href="/admirra/img/svg/sprite.svg#prev"></use></svg>
									</a>
									<span>&nbsp;</span>
									<a class="btn-nav" href="#">
										<svg><use href="/admirra/img/svg/sprite.svg#next"></use></svg>
									</a>
								</div>
							</div>
						</div>
					</div>
				</section>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'

const projects = ref([])
const loading = ref(true)

const fetchProjects = () => {
  loading.value = true
  setTimeout(() => {
    projects.value = [
      {
        id: '098409843080980',
        title: 'Дейтелинг Иркутск',
        channels: ['YANDEX_DIRECT', 'VK_ADS'],
        impressions: '1205',
        clicks: '1205',
        expenses: '90190',
        leads: '67',
        cpc: '67.00',
        cpa: '67.00',
        budgetRemaining: '10 200',
        trend: 15.6,
        status: 'Активен',
        createdAt: '09.03.2026'
      },
      {
        id: '098409843080981',
        title: 'Ремонт Квартир',
        channels: ['YANDEX_DIRECT'],
        impressions: '3500',
        clicks: '420',
        expenses: '45000',
        leads: '32',
        cpc: '107.00',
        cpa: '1406.00',
        budgetRemaining: '5 000',
        trend: 5.2,
        status: 'Активен',
        createdAt: '10.03.2026'
      },
      {
        id: '098409843080982',
        title: 'Автосервис',
        channels: ['VK_ADS'],
        impressions: '800',
        clicks: '102',
        expenses: '12000',
        leads: '15',
        cpc: '117.00',
        cpa: '800.00',
        budgetRemaining: '1 200',
        trend: -2.0,
        status: 'Остановлен',
        createdAt: '11.03.2026'
      }
    ]
    loading.value = false
    
    // Инициализация jQuery плагинов после загрузки данных
    nextTick(() => {
      if (window.jQuery) {
        window.jQuery('.dropdown').beefup({
          trigger: ".dropdown-head",
          content: ".dropdown-body",
          selfClose: true,
          animation: "fade",
        });
      }
    })
  }, 500)
}

const deleteProject = (projectId) => {
  if (confirm('Вы уверены, что хотите удалить этот проект?')) {
    projects.value = projects.value.filter(p => p.id !== projectId)
  }
}

onMounted(() => {
  fetchProjects()

  nextTick(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect();
    }
  });
})
</script>
