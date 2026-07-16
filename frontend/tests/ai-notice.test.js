/**
 * AiNotice 合规提示条组件单元测试。
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AiNotice from '../src/components/AiNotice.vue'

// el-icon 及图标为全局注册组件，测试中以 stub 替代
const globalStubs = {
  global: {
    stubs: {
      'el-icon': true,
      WarningFilled: true,
      InfoFilled: true,
    },
  },
}

describe('AiNotice', () => {
  it('默认渲染标准免责声明文案', () => {
    const wrapper = mount(AiNotice, globalStubs)
    expect(wrapper.text()).toContain('以上内容仅供参考，不构成正式法律意见')
  })

  it('默认 tone 为 info（浅灰）', () => {
    const wrapper = mount(AiNotice, globalStubs)
    expect(wrapper.classes()).toContain('info')
  })

  it('tone=warning 时应用警示样式', () => {
    const wrapper = mount(AiNotice, { props: { tone: 'warning' }, ...globalStubs })
    expect(wrapper.classes()).toContain('warning')
  })

  it('slot 内容覆盖默认文案', () => {
    const wrapper = mount(AiNotice, {
      slots: { default: 'AI生成内容仅供参考，请核实后使用' },
      ...globalStubs,
    })
    expect(wrapper.text()).toContain('AI生成内容仅供参考，请核实后使用')
    expect(wrapper.text()).not.toContain('不构成正式法律意见')
  })

  it('非法 tone 值不通过 validator', () => {
    const validator = AiNotice.props.tone.validator
    expect(validator('info')).toBe(true)
    expect(validator('warning')).toBe(true)
    expect(validator('danger')).toBe(false)
  })
})
