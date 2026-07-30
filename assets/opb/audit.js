/* 长图三项排版断言。渲染前必过，过不了 render() 直接拒绝出图。

   踩坑1（孤字行探针）：不能只取元素「最后一个文本节点」判字数——段落若以
   </b>。 这种「粗体片段 + 标点」收尾，DOM 里最后一个文本节点可能只有一个
   字符（那个句号），这样量只会恒报孤字，不管末行实际有多少字。必须用
   TreeWalker 遍历元素内*全部*文本节点、逐字符用 Range.getBoundingClientRect()
   取 rect.top，按「是否落在末行」分类计数，字符所属哪个文本节点不重要。

   踩坑2（溢出白名单）：.atm 这类装饰性氛围层用 position:absolute 把内容
   摆到视口外制造出血效果，是故意为之的「合法溢出」，不是排版事故。断言必须
   排除 overflow:hidden 或 position:absolute 的容器，否则每次渲染都会被这类
   装饰层刷屏式误报，教会用的人对断言脱敏（"反正总是报错，不用看"）。 */
(() => {
  const out = { bad: [], orphan: [], overflow: [] };

  // ① 坏断行：标题类文案是作者按语义手工断的行（<br> 数量 = 作者预期行数减一）。
  // 如果浏览器实际渲染出的行数超过声明，说明发生了作者没预料到的自动换行——
  // 手工断行的意图被打破了，必须整改文案或加宽容器，不能让浏览器替作者决定。
  document.querySelectorAll('h1,h2,h3,.act .n,.pour .q,.card h3').forEach(el => {
    const lh = parseFloat(getComputedStyle(el).lineHeight);
    if (!lh) return; // line-height 计算不出数值（如 normal）时无法换算行数，跳过
    const lines = Math.round(el.getBoundingClientRect().height / lh);
    const declared = el.innerHTML.split(/<br\s*\/?>/i).length;
    if (lines > declared) {
      out.bad.push({ t: el.textContent.trim().slice(0, 34), lines, declared });
    }
  });

  // ② 孤字行：末行字符数 < 3。单独一两个字挂在段落最后一行，读起来像排版事故。
  const measureLast = (el) => {
    const lh = parseFloat(getComputedStyle(el).lineHeight);
    const rect = el.getBoundingClientRect();
    if (!lh || Math.round(rect.height / lh) < 2) return null; // 单行文本没有「末行」这个概念
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const r = document.createRange();
    let count = 0, n;
    while ((n = walker.nextNode())) {
      const t = n.textContent;
      for (let i = 0; i < t.length; i++) {
        if (!t[i].trim()) continue; // 跳过空白字符，不计入行末字数
        r.setStart(n, i); r.setEnd(n, i + 1);
        const rc = r.getBoundingClientRect();
        if (rc.height === 0) continue; // 折叠的空白节点会给出零高度矩形，跳过
        if (rc.top >= rect.bottom - lh * 1.35) count++; // 落在末行带内（留 35% 行高容差）
      }
    }
    return count;
  };
  document.querySelectorAll('h1,h2,h3,.prose,.hook,.act .d,.ri .t,.pour .n,.qc .q,.stat .c')
    .forEach(el => {
      const c = measureLast(el);
      if (c !== null && c > 0 && c < 3) {
        out.orphan.push({ t: el.textContent.trim().slice(0, 30), last: c });
      }
    });

  // ③ 元素溢出：任何比容器宽的东西。absolute 或 overflow:hidden 的容器排除
  // （氛围层的白名单，见文件头踩坑2）。
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.overflow === 'hidden' || cs.position === 'absolute') return;
    if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 2) {
      out.overflow.push(el.className || el.tagName);
    }
  });

  out.docOverflow =
    document.documentElement.scrollWidth - document.documentElement.clientWidth;
  out.height = document.body.scrollHeight;
  return out;
})()
