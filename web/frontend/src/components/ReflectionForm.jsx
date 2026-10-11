import { useEffect, useState } from 'react'
import { useUiStore } from '../store/useUiStore.js'
import { useReflectionMutations, useReflections } from '../api/hooks.js'
import { normalizeReflections } from '../lib/normalize.js'
import { EXERCISES, DIR_NAME } from '../const/exercises.js'
import { message } from 'antd'

// 新建 / 编辑感悟弹窗（动作留空 = 训练日随笔；组号留空 = 动作级）
export default function ReflectionForm() {
  const formOpen = useUiStore((s) => s.formOpen)
  const formEditId = useUiStore((s) => s.formEditId)
  const formPrefill = useUiStore((s) => s.formPrefill)
  const closeForm = useUiStore((s) => s.closeForm)
  const today = useUiStore((s) => s.today)
  const { data: refData } = useReflections({})
  const { create, update } = useReflectionMutations()

  const [exercise, setExercise] = useState('')
  const [setRaw, setSetRaw] = useState('')
  const [date, setDate] = useState(today)
  const [content, setContent] = useState('')
  const [tagsRaw, setTagsRaw] = useState('')

  useEffect(() => {
    if (!formOpen) return
    const editing = formEditId ? normalizeReflections(refData).find((r) => r.id === formEditId) : null
    setExercise(editing ? editing.exercise || '' : formPrefill?.exercise || (formPrefill?.day ? '' : ''))
    setSetRaw(editing ? (editing.setIndex || '') : (formPrefill?.setIndex || ''))
    setDate(editing ? editing.date : formPrefill?.date || today)
    setContent(editing ? editing.content : '')
    setTagsRaw(editing ? (editing.tags || []).join(',') : '')
  }, [formOpen, formEditId, formPrefill, refData, today])

  if (!formOpen) return null

  const save = () => {
    if (!date || !content.trim()) {
      message.warning('日期、内容必填')
      return
    }
    const setIndex = setRaw.trim() ? parseInt(setRaw, 10) : null
    if (setRaw.trim() && (!setIndex || setIndex < 1)) {
      message.warning('组号需为正整数，或留空')
      return
    }
    const tags = tagsRaw
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter(Boolean)
    const direction = exercise ? EXERCISES.find((e) => e.label === exercise)?.direction || '' : ''

    const payload = {
      content: content.trim(),
      date,
      direction,
      exercise: exercise || null,
      set_index: setIndex,
      tags,
      source: '页面',
    }

    if (formEditId) {
      update.mutate(
        { id: formEditId, payload },
        {
          onSuccess: () => {
            message.success('已更新')
            closeForm()
          },
          onError: (e) => message.error(e.message),
        },
      )
    } else {
      create.mutate(payload, {
        onSuccess: () => {
          message.success('已新建')
          closeForm()
        },
        onError: (e) => message.error(e.message),
      })
    }
  }

  return (
    <div
      className="mask"
      style={{ position: 'fixed', inset: 0, background: 'rgba(8,10,14,.72)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) closeForm()
      }}
    >
      <div className="dlg" style={{ width: 420, maxWidth: '92vw', background: 'var(--panel2)', border: '1px solid #33415a', borderRadius: 12, padding: '18px 20px' }}>
        <h3 style={{ fontSize: 15, marginBottom: 14 }}>{formEditId ? '编辑感悟' : '新建感悟'}</h3>
        <div className="fld">
          <label>动作（留空 = 训练日随笔）</label>
          <select value={exercise} onChange={(e) => setExercise(e.target.value)}>
            <option value="">（训练日随笔）</option>
            {EXERCISES.map((e) => (
              <option key={e.id} value={e.label}>
                {e.label}（{DIR_NAME[e.direction]}）
              </option>
            ))}
          </select>
        </div>
        <div className="fld">
          <label>组号（不填 = 动作级 / 日级）</label>
          <input type="number" min="1" max="10" placeholder="如 2，代表第 2 组" value={setRaw} onChange={(e) => setSetRaw(e.target.value)} />
        </div>
        <div className="fld">
          <label>日期</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="fld">
          <label>内容</label>
          <textarea placeholder="这组最顺，肩胛锁死更稳…" value={content} onChange={(e) => setContent(e.target.value)} />
        </div>
        <div className="fld">
          <label>标签（逗号分隔，可空）</label>
          <input placeholder="发力感,技术点" value={tagsRaw} onChange={(e) => setTagsRaw(e.target.value)} />
        </div>
        <div className="dlg-acts" style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <button className="btn" onClick={closeForm}>取消</button>
          <button className="btn primary" onClick={save}>保存</button>
        </div>
      </div>
    </div>
  )
}
