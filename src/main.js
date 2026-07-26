(function () {
  'use strict';
  const version = 'Version: 2022.10.29';

  // ※下記の「5/168,259/498,......」という値は、TokusiNさんが作成して公開してくださった魔方陣の生データです。
  // 関連URL:
  //   https://twitter.com/toku51n/status/1533401499983749121
  //   https://twitter.com/toku51n/status/1533631580450615297
  //   https://github.com/TokusiN/AtanMagic/blob/main/data.txt
  const dataStr = `5/168,259/498,216/337,129/478,381/436,266/303,6/127,78/179,31/480,144/307,210/341,43/474,174/443,172/379,271/348,41/88
162/461,212/319,287/486,74/265,57/410,185/344,85/178,71/386,187/326,426/431,156/175,28/211,115/472,14/249,186/277,109/432
123/256,224/403,217/354,146/447,84/347,52/275,48/199,135/506,434/467,95/252,4/251,131/398,122/155,343/430,46/291,328/479
64/333,368/501,159/362,191/488,228/371,193/384,60/233,154/295,82/243,286/483,138/229,33/494,223/330,218/505,29/340,108/281
62/141,91/452,352/411,87/332,34/313,111/202,103/504,133/492,65/142,36/323,418/465,345/394,67/422,209/408,105/248,206/297
12/349,213/236,42/331,106/153,47/456,58/503,63/124,476/507,97/360,92/367,49/298,414/415,357/466,246/437,113/254,99/320
22/119,197/302,114/245,278/279,361/482,203/404,90/413,182/309,294/493,126/457,45/446,130/391,93/484,73/450,388/425,44/339
190/221,68/489,94/435,86/335,161/222,10/283,169/406,104/399,16/455,284/315,373/512,89/120,242/405,305/424,102/353,83/460
255/304,55/268,51/380,208/219,237/350,200/409,363/416,35/234,272/485,39/98,118/429,134/195,27/448,117/356,165/442,40/509
364/453,21/220,232/407,80/439,184/369,230/433,107/288,227/316,355/428,112/445,282/497,310/449,132/475,17/490,18/293,231/470
239/336,263/440,72/487,128/365,77/240,420/463,13/366,59/244,50/183,32/81,301/444,148/389,382/495,69/400,247/508,226/481
143/300,38/375,188/241,412/511,53/454,180/377,171/296,163/390,150/419,151/500,306/499,125/378,338/451,116/473,75/376,149/438
273/290,15/238,3/196,37/374,214/427,101/318,262/351,2/469,257/396,329/468,26/225,204/253,471/496,100/267,23/158,285/346
110/269,9/292,250/477,205/324,401/462,7/334,258/395,157/358,70/261,56/459,215/402,79/502,173/510,264/289,392/423,96/385
20/121,207/260,274/417,176/321,136/311,147/370,325/342,314/441,8/181,54/167,1/192,11/270,30/397,198/299,170/387,145/166
76/393,372/421,61/312,19/458,25/308,139/276,201/464,160/189,280/359,194/383,140/491,66/137,24/317,177/322,152/235,164/327`;

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const elems = {};
  let data = [];

  const defaultSpeedLevel = 2;
  const minSpeedLevel = 1;
  const maxSpeedLevel = 9;
  let processId = 0;
  let speedLevel = defaultSpeedLevel;
  let intervalTime;
  let isPlaying = false;
  let isFinished = false;
  const smallFontSize = '9px';

  const options = {
    omit: undefined,
    colorful: undefined,
  };

  window.addEventListener('load', init, false);

  async function init() {
    document.addEventListener('keydown', keydown, false);

    initData();

    document.getElementById('version-info').innerText = version;
    elems.svg = document.getElementById('svgBoard');
    elems.result = document.getElementById('result');

    elems.reset = document.getElementById('buttonReset');
    elems.stop = document.getElementById('buttonStop');
    elems.start = document.getElementById('buttonStart');
    elems.speedDown = document.getElementById('buttonSpeedDown');
    elems.speedUp = document.getElementById('buttonSpeedUp');
    elems.speedInfo = document.getElementById('speedInfo');

    intervalTime = speedLevelToIntervalTime(speedLevel);

    elems.reset.addEventListener('click', reset, false);
    elems.stop.addEventListener('click', stop, false);
    elems.start.addEventListener('click', start, false);
    elems.speedDown.addEventListener('click', speedDown, false);
    elems.speedUp.addEventListener('click', speedUp, false);

    hideElem(elems.reset);

    // オプションの初期化
    for (const optionName in options) {
      const elemOption = document.getElementById('options-' + optionName);
      options[optionName] = elemOption.checked;
      elemOption.addEventListener(
        'change',
        function () {
          options[optionName] = elemOption.checked;
        },
        false
      );
    }

    const size = 30;
    const offsetX = (500 - 30 * 16) / 2;
    const offsetY = offsetX;
    for (let y = 0; y < 16; ++y) {
      for (let x = 0; x < 16; ++x) {
        const numer = data[y][x].numer;
        const denom = data[y][x].denom;

        const g = createG();
        {
          const rect = createRect({
            x: size * x + offsetX,
            y: size * y + offsetY,
            width: size,
            height: size,
          });
          rect.setAttribute('fill', 'white');
          rect.setAttribute('stroke', 'green');
          rect.setAttribute('stroke-width', '0.5');
          rect.setAttribute('id', getFractionName(numer, denom));
          rect.setAttribute('class', 'fraction');
          g.appendChild(rect);
        }
        {
          const xx = size * x + offsetX;
          const yy = size * y + offsetY;
          const margin = 5;
          const line = createLine({
            x1: xx + margin,
            y1: yy + size / 2,
            x2: xx + size - margin,
            y2: yy + size / 2,
          });
          line.setAttribute('stroke', 'black');
          line.setAttribute('stroke-width', '0.5');
          g.appendChild(line);
        }

        {
          const text = createText({
            x: size * (x + 0.5) + offsetX,
            y: size * (y + 0.3) + offsetY,
            text: numer,
          });
          text.setAttribute('font-size', smallFontSize);
          text.setAttribute('id', numer);
          text.setAttribute('class', 'numer');
          g.appendChild(text);
        }
        {
          const text = createText({
            x: size * (x + 0.51) + offsetX,
            y: size * (y + 0.77) + offsetY,
            text: denom,
          });
          text.setAttribute('font-size', smallFontSize);
          text.setAttribute('id', denom);
          text.setAttribute('class', 'denom');
          g.appendChild(text);
        }
        elems.svg.appendChild(g);
      }
    }

    reset();
  }

  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

  function resetMainSvg() {
    for (const elem of document.getElementsByClassName('fraction')) {
      elem.setAttribute('fill', 'white');
    }
    for (const elem of document.getElementsByClassName('numer')) {
      unhighlightTextSvgElem(elem);
    }
    for (const elem of document.getElementsByClassName('denom')) {
      unhighlightTextSvgElem(elem);
    }
    elems.result.innerHTML = ''; // 描画済みの結果を消去します。
  }

  const colors = [
    '#eddbff',
    '#dbdbff',
    '#dbedff',
    '#dbffff',
    '#dbffed',
    '#dbffdb',
    '#edffdb',
    '#ffffdb',
    '#eddbff',
    '#dbdbff',
    '#dbedff',
    '#dbffff',
    '#dbffed',
    '#dbffdb',
    '#edffdb',
    '#ffffdb',
  ];

  function getFixedColor(i) {
    return options.colorful ? colors[i] : colors[0];
  }

  async function draw(fractions, pid) {
    resetMainSvg();
    while (pid === processId && !isPlaying) await sleep(50);

    const centerX = 750;
    const centerY = 250 + 5;

    let radian = 0;
    elems.svg.appendChild(elems.result);
    let idx = -1;
    for (const fraction of fractions) {
      idx++;
      if (pid !== processId) return;
      const g = createG();
      elems.result.appendChild(g);
      const numer = fraction.numer;
      const denom = fraction.denom;
      const atan = Math.atan(numer / denom);
      // console.log(`${numer} / ${denom}`);

      const ratio = 0.4;
      const points = [
        [centerX, centerY],
        [centerX + denom * 0.4, centerY],
        [centerX + denom * ratio, centerY - numer * ratio],
      ];

      const elemFraction = document.getElementById(
        getFractionName(numer, denom)
      );
      const elemNumer = document.getElementById(numer);
      const elemDenom = document.getElementById(denom);

      const fontSize = '18px';

      // 三角形
      const polygon = createPolygon({ points });
      polygon.setAttribute('fill', 'yellow');
      polygon.setAttribute('stroke', 'black');

      // 分母のテキスト
      const textDenom = createText({
        x: (points[0][0] + points[1][0]) / 2,
        y: points[0][1] + 16,
        text: denom,
      });
      textDenom.setAttribute('font-size', fontSize);
      textDenom.setAttribute('font-weight', 'bold');

      // 分子のテキスト
      const textNumer = createText({
        x: points[1][0] + 8,
        y: (points[1][1] + points[2][1]) / 2,
        text: numer,
      });
      textNumer.setAttribute('font-size', fontSize);
      textNumer.setAttribute('font-weight', 'bold');
      textNumer.setAttribute('text-anchor', 'start');

      if (pid === processId) elemFraction.setAttribute('fill', 'yellow');

      if (options.omit) {
        if (pid === processId) highlightTextSvgElem(elemNumer);
        if (pid === processId) highlightTextSvgElem(elemDenom);
        textDenom.setAttribute('fill', 'red');
        textNumer.setAttribute('fill', 'red');
        const deg = (-radian * 180) / Math.PI;
        g.setAttribute('transform', `rotate(${deg} ${centerX} ${centerY})`);
        g.appendChild(polygon);
        g.appendChild(textDenom);
        g.appendChild(textNumer);
        if (pid === processId) await sleep(intervalTime);
        while (pid === processId && !isPlaying) await sleep(50);
        if (pid === processId) unhighlightTextSvgElem(elemNumer);
        if (pid === processId) unhighlightTextSvgElem(elemDenom);
        textDenom.setAttribute('fill', 'black');
        textNumer.setAttribute('fill', 'black');

        g.innerHTML = ''; // 描いた図形を消去。

        g.appendChild(polygon);
        const fixedColor = getFixedColor(idx);
        polygon.setAttribute('fill', fixedColor);
        if (pid === processId) elemFraction.setAttribute('fill', fixedColor);
      } else {
        // 横線（分母）に注目
        if (pid === processId) highlightTextSvgElem(elemDenom);
        g.appendChild(polygon);
        g.appendChild(textDenom);
        g.appendChild(textNumer);
        {
          const line = createLine({
            x1: points[0][0],
            y1: points[0][1],
            x2: points[1][0],
            y2: points[1][1],
          });
          line.setAttribute('stroke', 'red');
          line.setAttribute('stroke-width', '3');
          g.appendChild(line);

          textDenom.setAttribute('fill', 'red');
        }
        if (pid === processId) await sleep(intervalTime);
        while (pid === processId && !isPlaying) await sleep(50);
        if (pid === processId) unhighlightTextSvgElem(elemDenom);
        textDenom.setAttribute('fill', 'black');

        g.innerHTML = ''; // 描いた図形を消去。

        // 縦線（分子）に注目
        if (pid === processId) highlightTextSvgElem(elemNumer);
        g.appendChild(polygon);
        g.appendChild(textDenom);
        g.appendChild(textNumer);
        {
          const line = createLine({
            x1: points[2][0],
            y1: points[2][1],
            x2: points[1][0],
            y2: points[1][1],
          });
          line.setAttribute('stroke', 'red');
          line.setAttribute('stroke-width', '3');
          g.appendChild(line);

          textNumer.setAttribute('fill', 'red');
        }
        if (pid === processId) await sleep(intervalTime);
        while (pid === processId && !isPlaying) await sleep(50);
        if (pid === processId) unhighlightTextSvgElem(elemNumer);
        textNumer.setAttribute('fill', 'black');

        g.innerHTML = ''; // 描いた図形を消去。

        let fixedColor;
        // 三角形を回転
        {
          const num = Math.floor(intervalTime / 30) + 1;
          for (let i = 0; i <= num; ++i) {
            const deg = (((-radian * 180) / Math.PI) * i) / num;
            g.innerHTML = '';
            g.setAttribute('transform', `rotate(${deg} ${centerX} ${centerY})`);
            g.appendChild(polygon);
            if (i !== num) {
              g.appendChild(textDenom);
              g.appendChild(textNumer);
            }
            if (pid === processId) await sleep(intervalTime / num);
            while (pid === processId && !isPlaying) await sleep(50);
          }
          fixedColor = getFixedColor(idx);
          polygon.setAttribute('fill', fixedColor);
        }
        if (pid === processId) elemFraction.setAttribute('fill', fixedColor);
      }
      radian += atan;
    }
    if (pid === processId) await sleep(intervalTime * 2);
    while (pid === processId && !isPlaying) await sleep(50);

    const precision = 15;
    const pi = (radian / 2).toPrecision(precision);
    // atan(x)の和が2πになるかの確認。
    // ※厳密に一致しているかのチェックにはなっていません。
    //   厳密な検証に関しては、@hamukazuさんが検出用プログラムを公開しています。
    //   https://twitter.com/hamukazu/status/1533726390629019648
    if (pi !== Math.PI.toPrecision(precision)) {
      console.warn('Low precision.');
    }
    // console.log(`${pi} * 2`);
  }

  function highlightTextSvgElem(elem) {
    if (elem === undefined) return;
    elem.setAttribute('fill', 'red');
    elem.setAttribute('font-weight', 'bold');
    elem.setAttribute('font-size', '12px');
  }

  function unhighlightTextSvgElem(elem) {
    if (elem === undefined) return;
    elem.setAttribute('fill', 'black');
    elem.setAttribute('font-weight', 'normal');
    elem.setAttribute('font-size', smallFontSize);
  }

  function createG() {
    const g = document.createElementNS(SVG_NS, 'g');
    return g;
  }

  function createLine(param) {
    const line = document.createElementNS(SVG_NS, 'line');
    line.setAttribute('x1', param.x1);
    line.setAttribute('y1', param.y1);
    line.setAttribute('x2', param.x2);
    line.setAttribute('y2', param.y2);
    return line;
  }

  function createRect(param) {
    const rect = document.createElementNS(SVG_NS, 'rect');
    rect.setAttribute('x', param.x);
    rect.setAttribute('y', param.y);
    rect.setAttribute('width', param.width);
    rect.setAttribute('height', param.height);
    return rect;
  }

  function createPolygon(param) {
    const polygon = document.createElementNS(SVG_NS, 'polygon');
    let points = '';
    for (const point of param.points) {
      if (points !== '') points += ' ';
      points += `${point[0]},${point[1]}`;
    }
    polygon.setAttribute('points', points);
    return polygon;
  }

  function createText(param) {
    const text = document.createElementNS(SVG_NS, 'text');
    text.setAttribute('x', param.x);
    text.setAttribute('y', param.y);
    text.textContent = param.text;
    text.setAttribute('dominant-baseline', 'middle');
    text.setAttribute('text-anchor', 'middle');
    return text;
  }

  function initData() {
    data = [];
    const nums = {};

    let y = 0;
    for (const line of dataStr.split('\n')) {
      data[y] = [];
      for (const num of line.split(',')) {
        const ab = num.split('/');
        const a = Number(ab[0]);
        const b = Number(ab[1]);
        nums[a] = true;
        nums[b] = true;
        // 真分数であるかの確認。
        if (a >= b) {
          console.warn(`${a}/${b}は真分数ではありません。`);
        }
        // 既約分数であるかの確認。
        if (gcd(a, b) !== 1) {
          console.error(`${a} と ${b} の最小公倍数は ${gcd(a, b)} です。`);
        }
        data[y].push({ numer: a, denom: b });
      }
      y++;
    }

    // 1～512が重複なく含まれているかの確認。
    for (let i = 0; i < 512; ++i) {
      if (nums[i + 1] === undefined) {
        console.warn(`${i + 1}が含まれていません。`);
      }
    }
  }

  function getFractionName(numer, denom) {
    return `${numer}/${denom}`;
  }

  function speedLevelToIntervalTime(speedLevel) {
    elems.speedInfo.innerText = '速度レベル: ' + '★'.repeat(speedLevel);
    return 2 ** (11 - speedLevel);
  }

  async function reset() {
    isFinished = false;
    isPlaying = false;
    hideElem(elems.reset);
    hideElem(elems.stop);
    showElem(elems.start);
    resetMainSvg();

    processId = (processId + 1) % 1000000;
    const pid = processId;
    // 横
    for (let i = 0; i < 16; ++i) {
      await draw(data[i], pid);
      if (pid !== processId) return;
    }
    // 縦
    for (let i = 0; i < 16; ++i) {
      const fractions = [];
      for (let j = 0; j < 16; ++j) {
        fractions.push(data[j][i]);
      }
      await draw(fractions, pid);
      if (pid !== processId) return;
    }
    // ＼
    {
      const fractions = [];
      for (let i = 0; i < 16; ++i) {
        fractions.push(data[i][i]);
      }
      await draw(fractions, pid);
      if (pid !== processId) return;
    }
    // ／
    {
      const fractions = [];
      for (let i = 0; i < 16; ++i) {
        fractions.push(data[i][15 - i]);
      }
      await draw(fractions, pid);
    }
    hideElem(elems.stop);
    hideElem(elems.start);
    isFinished = true;
  }

  function stop() {
    if (!isPlaying) return;
    isPlaying = false;
    hideElem(elems.stop);
    showElem(elems.start);
  }

  function start() {
    if (isPlaying) return;
    isPlaying = true;
    showElem(elems.reset);
    showElem(elems.stop);
    hideElem(elems.start);
  }

  function speedDown() {
    if (speedLevel === minSpeedLevel) return;
    showElem(elems.speedUp);
    speedLevel--;
    intervalTime = speedLevelToIntervalTime(speedLevel);

    if (speedLevel === minSpeedLevel) {
      hideElem(elems.speedDown);
      return;
    }
  }

  function speedUp() {
    if (speedLevel === maxSpeedLevel) return;
    showElem(elems.speedDown);
    speedLevel++;
    intervalTime = speedLevelToIntervalTime(speedLevel);

    if (speedLevel === maxSpeedLevel) {
      hideElem(elems.speedUp);
      return;
    }
  }

  function keydown(e) {
    if (e.key === 'r') {
      reset();
    } else if (e.key === ' ') {
      e.preventDefault();
      if (isFinished) return;
      if (isPlaying) {
        stop();
      } else {
        start();
      }
    } else if (e.shiftKey) {
      e.preventDefault();
      if (e.key === 'ArrowDown') {
        speedDown();
      } else if (e.key === 'ArrowUp') {
        speedUp();
      }
    }
  }

  function gcd(x, y) {
    if (x % y) {
      return gcd(y, x % y);
    } else {
      return y;
    }
  }

  function showElem(elem) {
    if (elem === undefined) return;
    elem.style.display = 'block';
  }

  function hideElem(elem) {
    if (elem === undefined) return;
    elem.style.display = 'none';
  }
})();
