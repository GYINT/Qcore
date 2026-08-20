---
fields:
  intent:     {type: string, required: true}
  domain:     {type: string, required: true}
  confidence: {type: float, required: true}
  D:          {type: string, required: false}
  complexity: {type: string, required: false}
  skeleton:   {type: string, required: true}
  form:       {type: string, required: true}
  depth:      {type: string, required: true}
---
【路由】意图={intent} · 领域={domain} · 置信度={confidence} · D={D} · 复杂度={complexity}
【形态】{form} · 骨架={skeleton} · 深度={depth}
