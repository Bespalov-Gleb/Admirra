<template>
  <div class="space-y-6">
    <!-- Заголовок и кнопки -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Продукты</h1>
      <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
        <button
          @click="showAddProductModal = true"
          class="flex items-center justify-center gap-2 px-4 py-2.5 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium w-full sm:w-auto order-2 sm:order-1"
        >
          <PlusIcon class="w-5 h-5" />
          <span>Добавить продукт</span>
        </button>
        <div class="flex flex-wrap items-center justify-end gap-3 order-1 sm:order-2">
          <button
            class="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <ArrowDownTrayIcon class="w-4 h-4" />
            <span>Экспорт данных</span>
          </button>
          <div class="relative">
            <select class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
              <option>Сортировать по: ID</option>
              <option>Сортировать по: Названию</option>
              <option>Сортировать по: Цене</option>
              <option>Сортировать по: Дате</option>
              <option>Сортировать по: Статусу</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Таблица -->
    <div class="bg-white rounded-lg shadow border border-gray-200 flex flex-col overflow-hidden" style="max-height: calc(100vh - 200px)">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 sm:p-6 border-b border-gray-200 flex-shrink-0">
        <div></div>
      </div>
      <div class="overflow-x-auto overflow-y-auto flex-1 min-h-0" style="max-height: calc(100vh - 350px); -webkit-overflow-scrolling: touch">
        <table class="w-full" style="min-width: 640px">
          <thead class="bg-white divide-y divide-gray-200 border-b border-gray-200 sticky top-0 z-10">
            <tr>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Название
              </th>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Статус
              </th>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                Категория
              </th>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                Цена
              </th>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                Дата
              </th>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">
                ID
              </th>
              <th class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                Действия
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="product in paginatedProducts" :key="product.id" class="hover:bg-gray-50">
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ product.name }}
              </td>
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap hidden sm:table-cell">
                <span :class="getStatusClass(product.status)" class="px-2 py-1 text-xs font-medium rounded-full">
                  {{ product.status }}
                </span>
              </td>
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                {{ product.category }}
              </td>
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                {{ product.price }}
              </td>
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden lg:table-cell">
                {{ product.date }}
              </td>
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden lg:table-cell">
                {{ product.productId || product.id }}
              </td>
              <td class="px-3 sm:px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div class="relative inline-block">
                  <button
                    :data-product-id="product.id"
                    @click="toggleDropdown(product.id)"
                    class="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <EllipsisHorizontalIcon class="w-5 h-5" />
                  </button>
                  <Teleport to="body">
                    <div
                      v-if="openDropdownId === product.id"
                      :style="getDropdownStyle(product.id)"
                      class="dropdown-menu fixed w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50"
                      @click.stop
                    >
                    <button
                      @click="handleAction('view', product)"
                      class="w-full text-left px-4 py-2 hover:bg-gray-100 transition-colors flex items-center gap-2 text-sm text-gray-700"
                    >
                      <EyeIcon class="w-4 h-4" />
                      Просмотр
                    </button>
                    <button
                      @click="handleAction('edit', product)"
                      class="w-full text-left px-4 py-2 hover:bg-gray-100 transition-colors flex items-center gap-2 text-sm text-gray-700"
                    >
                      <PencilIcon class="w-4 h-4" />
                      Редактировать
                    </button>
                    <button
                      @click="handleAction('duplicate', product)"
                      class="w-full text-left px-4 py-2 hover:bg-gray-100 transition-colors flex items-center gap-2 text-sm text-gray-700"
                    >
                      <DocumentDuplicateIcon class="w-4 h-4" />
                      Дублировать
                    </button>
                    <button
                      @click="handleAction('delete', product)"
                      class="w-full text-left px-4 py-2 hover:bg-gray-100 transition-colors flex items-center gap-2 text-sm text-red-600"
                    >
                      <TrashIcon class="w-4 h-4" />
                      Удалить
                    </button>
                    </div>
                  </Teleport>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Пагинация -->
      <div class="flex items-center justify-center px-2 sm:px-4 md:px-6 py-3 sm:py-4 border-t border-gray-200 bg-gray-50 overflow-x-auto flex-shrink-0">
        <div class="flex items-center gap-1 flex-wrap justify-center min-w-0">
          <button
            @click="goToPreviousPage"
            :disabled="currentPage === 1"
            :class="[
              'flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-lg text-xs sm:text-sm font-medium transition-all flex-shrink-0',
              currentPage === 1
                ? 'text-gray-400 cursor-not-allowed bg-white border border-gray-200'
                : 'text-gray-700 hover:bg-white hover:border-gray-300 border border-gray-200 bg-white hover:shadow-sm'
            ]"
          >
            <ChevronLeftIcon class="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
          
          <template v-for="page in visiblePages" :key="page">
            <button
              v-if="page !== 'ellipsis'"
              @click="currentPage = page"
              :class="[
                'flex items-center justify-center min-w-[32px] sm:min-w-[36px] h-8 sm:h-9 px-2 sm:px-3 rounded-lg text-xs sm:text-sm font-medium transition-all flex-shrink-0',
                currentPage === page
                  ? 'bg-gray-800 text-white shadow-sm'
                  : 'text-gray-700 hover:bg-white hover:border-gray-300 border border-gray-200 bg-white hover:shadow-sm'
              ]"
            >
              {{ page }}
            </button>
            <span
              v-else
              class="px-1 sm:px-2 text-gray-400 text-xs sm:text-sm flex-shrink-0"
            >
              ...
            </span>
          </template>

          <button
            @click="goToNextPage"
            :disabled="currentPage === totalPages"
            :class="[
              'flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-lg text-xs sm:text-sm font-medium transition-all flex-shrink-0',
              currentPage === totalPages
                ? 'text-gray-400 cursor-not-allowed bg-white border border-gray-200'
                : 'text-gray-700 hover:bg-white hover:border-gray-300 border border-gray-200 bg-white hover:shadow-sm'
            ]"
          >
            <ChevronRightIcon class="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Модалка добавления продукта -->
    <AddProductModal
      v-model:is-open="showAddProductModal"
      @submit="handleAddProduct"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Teleport } from 'vue'
import {
  PlusIcon,
  ArrowDownTrayIcon,
  EllipsisHorizontalIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  PencilIcon,
  DocumentDuplicateIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'
import AddProductModal from './AddProductModal.vue'

const products = ref([
  { id: 1, name: "Macbook Pro 15'", status: 'Available', category: 'Laptops', price: '$2 999.00', date: '20 Jan, 2022', productId: '39842-231' },
  { id: 2, name: "Macbook Pro 13'", status: 'In Review', category: 'Laptops', price: '$2 999.00', date: '22 Feb, 2022', productId: '39842-231' },
  { id: 3, name: 'iPhone 13 Mini', status: 'Sold Out', category: 'Phones', price: '$2 999.00', date: '22 Feb, 2022', productId: '39842-231' },
  { id: 4, name: 'iPhone 14', status: 'Preorder', category: 'Phones', price: '$2 999.00', date: '22 Feb, 2022', productId: '39842-231' },
  { id: 5, name: 'AirPods 2', status: 'Available', category: 'Electronics', price: '$2 999.00', date: '22 Feb, 2022', productId: '39842-231' }
])

const currentPage = ref(4)
const itemsPerPage = 1
const totalPagesCount = 20
const openDropdownId = ref(null)
const showAddProductModal = ref(false)
const dropdownPositions = ref({})

const totalPages = computed(() => totalPagesCount)

const paginatedProducts = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return products.value.slice(start, end)
})

const visiblePages = computed(() => {
  const pages = []
  const current = currentPage.value
  const total = totalPages.value
  
  // Всегда показываем первую страницу
  if (current <= 3) {
    // Если мы близко к началу, показываем: 1, 2, 3, 4, 5, ..., 20
    for (let i = 1; i <= Math.min(5, total); i++) {
      pages.push(i)
    }
    if (total > 5) {
      pages.push('ellipsis')
      pages.push(total)
    }
  } else if (current >= total - 2) {
    // Если мы близко к концу, показываем: 1, ..., 16, 17, 18, 19, 20
    pages.push(1)
    if (total > 5) {
      pages.push('ellipsis')
    }
    for (let i = Math.max(1, total - 4); i <= total; i++) {
      pages.push(i)
    }
  } else {
    // Если мы в середине, показываем: 1, ..., 3, 4, 5, ..., 20
    pages.push(1)
    pages.push('ellipsis')
    for (let i = current - 1; i <= current + 1; i++) {
      pages.push(i)
    }
    pages.push('ellipsis')
    pages.push(total)
  }
  
  return pages
})

const getStatusClass = (status) => {
  const classes = {
    'Available': 'bg-green-100 text-green-800',
    'In Review': 'bg-yellow-100 text-yellow-800',
    'Sold Out': 'bg-red-100 text-red-800',
    'Preorder': 'bg-blue-100 text-blue-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

const toggleDropdown = async (id) => {
  if (openDropdownId.value === id) {
    openDropdownId.value = null
  } else {
    openDropdownId.value = id
    await nextTick()
    updateDropdownPosition(id)
  }
}

const updateDropdownPosition = (id) => {
  const button = document.querySelector(`[data-product-id="${id}"]`)
  if (button) {
    const rect = button.getBoundingClientRect()
    dropdownPositions.value[id] = {
      top: `${rect.bottom + 8}px`,
      right: `${window.innerWidth - rect.right}px`
    }
  }
}

const getDropdownStyle = (id) => {
  const pos = dropdownPositions.value[id]
  if (pos) {
    return {
      top: pos.top,
      right: pos.right
    }
  }
  return {}
}

const closeDropdown = () => {
  openDropdownId.value = null
}

const handleAction = (action, product) => {
  closeDropdown()
  console.log(action, product)
  // Здесь можно добавить логику для каждого действия
}

const goToPreviousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const goToNextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const handleAddProduct = (productData) => {
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const day = date.getDate()
    const month = months[date.getMonth()]
    const year = date.getFullYear()
    return `${day} ${month}, ${year}`
  }
  
  const newProduct = {
    id: products.value.length + 1,
    name: productData.name,
    status: productData.status,
    category: productData.category,
    price: productData.price,
    date: formatDate(productData.date),
    productId: productData.id
  }
  products.value.unshift(newProduct)
  console.log('Product added:', newProduct)
}

// Закрытие dropdown при клике вне его
const handleClickOutside = (event) => {
  if (!openDropdownId.value) return
  
  const target = event.target
  // Проверяем, не кликнули ли мы на кнопку открытия dropdown
  const button = target.closest(`[data-product-id="${openDropdownId.value}"]`)
  // Проверяем, не кликнули ли мы внутри самого dropdown
  const dropdown = target.closest('.dropdown-menu')
  
  // Если клик не на кнопке и не внутри dropdown, закрываем
  if (!button && !dropdown) {
    closeDropdown()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

