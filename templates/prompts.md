# 提示词模板

> `<尖括号>` 是要填的槽位。固定段（STYLE / CHAR / SCENE / NO_TEXT）定稿后**原样复用，不要改写**。
> 建议每段存成一个 `.txt`，用 `gen_image.py --prompt-file` 按顺序拼接。
> 提示词用英文写，对图像/视频模型更稳；人物名用描述代替（the girl / the tall man），不要用中文名。

---

## 1. STYLE（画风段，全剧固定）

```
Style: <媒介：2D anime cel-shaded illustration / stylized 3D animated feature film still /
traditional Chinese ink-wash painting / painterly digital illustration>,
<线条：clean thin line art / no outlines / soft brush edges>,
<上色：flat colors with two-tone shading / soft gradients / rich textured brushwork>,
<光影：cinematic warm key light and soft rim light / high-contrast noir lighting>,
<质感关键词 3 个>.
NOT a photograph, not photorealistic, not a real person.
```

## 2. CHAR（角色段，每个角色一份，每套服装一份）

```
<称呼：The girl / The young man / The old swordsman> is <年龄> years old, <民族/种族>,
<体型>, <发型 + 发色>, <1 个远处就能认出的标志：a red hair ribbon / a scar-free face with
round glasses / a white fur collar>, wears <服装：颜色 + 款式，具体到每件>.
```
规则：不用左右不对称的特征（单边发卡、胎记）；同框角色的标志颜色要不同。

## 3. SCENE（场景段，每个反复出现的场景一份）

```
Setting: <地点>, <时代/风格>, <布局：门在左、窗在右后方>, <时间与天气>,
<主光源方向与色温：warm sunlight from a window on the LEFT>, <固定陈设 3–5 件>.
```

## 4. NO_TEXT（固定）

```
Absolutely no text, no letters, no numbers, no signs, no watermark, no logo, no subtitles
anywhere in the image.
```

---

## 5. 镜头段：首帧

```
<景别：Close-up / Medium shot / Medium-wide shot / Wide shot>, <9:16 vertical portrait /
16:9 widescreen landscape>.
Camera <高度：at eye level / low angle / high angle>, <角度：three-quarter side angle /
rear-diagonal / profile>, NOT <不要的：frontal symmetrical shot / overhead>.
<角色A> <位置：on the LEFT / RIGHT / CENTER>, <姿势>, <视线：looking at <谁/哪里>>,
<表情>. Eyes on the <38% / 62%> <vertical / horizontal> line.
<角色B> <位置>, <姿势>, <视线>, <表情>.
Their postures differ clearly: <A 怎样>, <B 怎样>.
In the BACKGROUND, <旁观者>, facing <主体>, <状态>.
Empty space <above their heads / on the side she will lean into / along the track ahead>.
<光线>. <风向：hair, grass and cloth all drift toward the LEFT>.
No <多余物件1>, no <多余物件2>, no other people.
```

## 6. 镜头段：尾帧（单独生成时用；**更推荐用第 7 条图生图**）

```
Same <景别>, same camera, same framing as the first frame.
<只写一个变化的结果：The girl has now leaned her head onto his shoulder>.
<不变的元素逐项写>: <天色/墙面/灯/地面> IDENTICAL to the first frame.
<其他人> has not moved.
```

## 7. 图生图改图（锁背景，最常用）

```
Edit ONLY <要改的那一处，具体到部位：the girl's head and neck / the boy's hair>:
<改成什么：she now sits upright, her head NOT touching him, a clear gap between them>.
<保持不变的逐项列出：same face, same hairstyle with <标志>, same clothes, same hands,
same seated position>. <其他人> stays exactly the same.
CRITICAL — EVERYTHING ELSE IS FROZEN: keep the camera angle, framing, crop, the background
(<逐项点名：sky, mountains, river, trees, ground, props>), the light direction and colour
grading EXACTLY as in the input image. Do NOT move, add, remove, resize or rearrange anything
not named above.
<STYLE 简版：Same <画风> rendering as the input>. <NO_TEXT>
```
一次只改一处；要改多处就分多次，每次检查。

## 8. 降写实（视频平台报"可能含真人"时用）

```
Convert this image into a clearly STYLIZED <2D / 3D> animation film still.
CRITICAL — GEOMETRY IS FROZEN: keep the composition, camera angle, framing, crop, character
positions, poses, hand positions, gaze, clothing, props, background and light EXACTLY.
CHANGE ONLY THE SURFACE RENDERING: smooth stylized skin with no pores, simplified facial
planes, slightly larger clean eyes, hair as clean sculpted strands, matte fabric.
Must read unmistakably as an animated feature still, NOT a photograph, NOT a real person.
<NO_TEXT>
```

## 9. 角色设定图（三视图）

```
Character turnaround sheet of <CHAR 段>. Three full-body views side by side: front view,
side view, back view, same character, same outfit, neutral standing pose, arms relaxed.
Below: four head close-ups with expressions: neutral, smiling, surprised, sad.
Plain light grey background, even studio lighting. <STYLE>. <NO_TEXT>
```

---

## 10. MOTION（视频运动提示词）

```
<主体> <动作1>, then <动作2>.
<其他人> does not move at all.
<环境小动态：Hair and grass stir slightly in the breeze; the water flows slowly>.
The light stays constant.
The camera <stays completely fixed / slowly pushes in / slowly pulls back / tracks sideways
with them>.
Same place, same background throughout, no cut, no scene change.
<不说话：Nobody opens their mouth. / 说话：<角色> speaks calmly, small natural mouth movements.>
No text in the image.
```

运镜与首尾帧的关系：首尾同构图 → `fixed`；尾帧更远 → `pulls back`；尾帧更近 → `pushes in`。

---

## 11. 中文台词写法（配音）

- 中文约 **4–5 字/秒**；镜头 3 秒，台词最多约 12 字
- 一句只表达一个意思；长句就拆成两镜
- 标点决定停顿：逗号短停，省略号长停（适合梦话、迟疑）
