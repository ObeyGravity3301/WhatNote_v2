import React, { useRef, useEffect, useState, useCallback } from 'react';

/**
 * RadialMindMap - 径向思维导图组件
 * 展示PDF文档的层级结构（文件 → 分段 → 细分 → 页码）
 */
const RadialMindMap = ({ 
  pdfFilename, 
  outline, 
  subdivisions, 
  onPageClick
}) => {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [tree, setTree] = useState(null);
  const [scale, setScale] = useState(1);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [maxDisplayDepth, setMaxDisplayDepth] = useState(3); // 最大显示层级 (0=文件, 1=分段, 2=细分, 3=页码)

  // 1. 构建树结构（根据maxDisplayDepth裁剪）
  const buildTree = useCallback(() => {
    if (!outline || !subdivisions) return null;

    const root = {
      id: 'root',
      label: pdfFilename || 'Document',
      level: 0,
      children: []
    };

    // Level 1: 分段
    if (maxDisplayDepth >= 1) {
      outline.forEach((section, sIdx) => {
        const sectionNode = {
          id: `s-${sIdx}`,
          label: section.title || section.section_title || `Section ${sIdx + 1}`,
          level: 1,
          pageRange: [section.page_start, section.page_end],
          children: []
        };

        // Level 2: 细分
        if (maxDisplayDepth >= 2) {
          const subdivision = subdivisions[sIdx];
          if (subdivision?.subdivisions && Array.isArray(subdivision.subdivisions)) {
            subdivision.subdivisions.forEach((sub, subIdx) => {
              const subNode = {
                id: `s-${sIdx}-${subIdx}`,
                label: sub.title || `Subsection ${subIdx + 1}`,
                level: 2,
                pageRange: [sub.page_start, sub.page_end],
                children: []
              };

              // Level 3: 页码节点
              if (maxDisplayDepth >= 3) {
                for (let p = sub.page_start; p <= sub.page_end; p++) {
                  subNode.children.push({
                    id: `s-${sIdx}-${subIdx}-p${p}`,
                    label: `${p}`,
                    level: 3,
                    page: p,
                    children: []
                  });
                }
              }

              sectionNode.children.push(subNode);
            });
          }
        }

        root.children.push(sectionNode);
      });
    }

    return root;
  }, [pdfFilename, outline, subdivisions, maxDisplayDepth]);

  // 2. 计算径向布局（自适应防重叠算法）
  const calculateRadialLayout = useCallback((tree, centerX, centerY, baseRadius) => {
    if (!tree) return null;

    // Step 1: 收集每一层的所有节点
    const levels = [];
    const collectByLevel = (node, depth = 0) => {
      if (!levels[depth]) levels[depth] = [];
      levels[depth].push(node);
      if (node.children) {
        node.children.forEach(child => collectByLevel(child, depth + 1));
      }
    };
    collectByLevel(tree);
    
    console.log('各层节点数:', levels.map(l => l.length));
    
    // Step 2: 动态计算每层的最小安全半径
    const calculateMinRadius = (nodeCount, depth) => {
      // 估算节点尺寸（包含文字和边距）
      const nodeSizes = {
        0: { width: 140, height: 40 },  // 根节点（文件名）
        1: { width: 120, height: 32 },  // 分段
        2: { width: 100, height: 28 },  // 细分
        3: { width: 60, height: 24 }    // 页码
      };
      
      const nodeSize = nodeSizes[depth] || nodeSizes[3];
      
      if (nodeCount === 0) return 0;
      if (nodeCount === 1) return baseRadius * (depth + 1);
      
      // 使用弦长公式计算最小半径，确保节点不重叠
      // 弦长 = 2 * r * sin(θ/2)
      // 要求弦长 >= 节点宽度 * 1.3 (留30%安全间距)
      const angleStep = (2 * Math.PI) / nodeCount;
      const minChord = nodeSize.width * 1.3;
      const minRadius = minChord / (2 * Math.sin(angleStep / 2));
      
      return minRadius;
    };
    
    // Step 3: 从外向内计算实际层级半径（确保单调递减）
    const maxDepth = levels.length - 1;
    const levelRadius = [];
    
    // 先计算最外层（叶子）的半径
    const leafCount = levels[maxDepth]?.length || 0;
    const leafMinRadius = calculateMinRadius(leafCount, maxDepth);
    levelRadius[maxDepth] = Math.max(leafMinRadius, baseRadius * 5);
    
    console.log(`第${maxDepth}层（页码）: ${leafCount}个节点, 最小半径=${Math.round(leafMinRadius)}px, 实际半径=${Math.round(levelRadius[maxDepth])}px`);
    
    // 从外向内依次计算中间层
    for (let depth = maxDepth - 1; depth >= 1; depth--) {
      const nodeCount = levels[depth]?.length || 0;
      const minRadius = calculateMinRadius(nodeCount, depth);
      
      // 层间距：固定距离
      const layerGap = baseRadius * 2;
      
      // 当前层的上限：必须比外层小至少一个层间距
      const maxAllowed = levelRadius[depth + 1] - layerGap;
      
      // 如果该层的最小半径已经超过上限，说明外层半径不够大
      if (minRadius > maxAllowed) {
        // 向外扩展：重新计算外层及更外层的半径
        console.warn(`⚠️ 第${depth}层需要半径${Math.round(minRadius)}px，但外层限制为${Math.round(maxAllowed)}px，需要向外扩展`);
        
        // 从当前层开始向外重新计算
        let requiredRadius = minRadius;
        for (let d = depth; d <= maxDepth; d++) {
          levelRadius[d] = requiredRadius;
          requiredRadius += layerGap; // 每向外一层，增加一个层间距
        }
        
        levelRadius[depth] = minRadius;
        console.log(`  → 重新调整后，第${depth}层实际半径=${Math.round(levelRadius[depth])}px`);
      } else {
        // 正常情况：取最小半径和上限之间的较大值
        levelRadius[depth] = Math.max(minRadius, maxAllowed - layerGap * 0.5);
        console.log(`第${depth}层: ${nodeCount}个节点, 最小半径=${Math.round(minRadius)}px, 实际半径=${Math.round(levelRadius[depth])}px`);
      }
    }
    
    // Level 0 固定在中心
    levelRadius[0] = 0;
    
    console.log('✅ 最终层级半径:', levelRadius.map(r => Math.round(r)));
    
    // Step 4: 最外层均匀分布
    const leafNodes = levels[maxDepth];
    const totalLeaves = leafNodes.length;
    
    leafNodes.forEach((leaf, idx) => {
      const angle = (idx / totalLeaves) * 2 * Math.PI - Math.PI / 2;
      leaf.angle = angle;
      const radius = levelRadius[maxDepth];
      leaf.x = centerX + radius * Math.cos(angle);
      leaf.y = centerY + radius * Math.sin(angle);
    });
    
    // Step 5: 从外向内，父节点位于子节点的平均角度
    for (let depth = maxDepth - 1; depth >= 0; depth--) {
      const nodesAtDepth = levels[depth];
      const radius = levelRadius[depth];
      
      nodesAtDepth.forEach(node => {
        if (depth === 0) {
          // 根节点在中心
          node.x = centerX;
          node.y = centerY;
          node.angle = 0;
        } else if (node.children && node.children.length > 0) {
          // 计算子节点的平均角度
          const childAngles = node.children.map(c => c.angle);
          const avgAngle = childAngles.reduce((sum, a) => sum + a, 0) / childAngles.length;
          
          node.angle = avgAngle;
          node.x = centerX + radius * Math.cos(avgAngle);
          node.y = centerY + radius * Math.sin(avgAngle);
        } else {
          // 没有子节点但不是叶子节点（异常情况）
          const angle = Math.random() * 2 * Math.PI;
          node.angle = angle;
          node.x = centerX + radius * Math.cos(angle);
          node.y = centerY + radius * Math.sin(angle);
        }
      });
    }
    
    return tree;
  }, []);

  // 3. 监听容器尺寸变化
  useEffect(() => {
    if (!containerRef.current) return;

    const updateDimensions = () => {
      const rect = containerRef.current.getBoundingClientRect();
      setDimensions({
        width: rect.width,
        height: rect.height
      });
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(updateDimensions);
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // 4. 初始化树结构
  useEffect(() => {
    console.log(`🔄 重新构建思维导图 (显示层级: ${maxDisplayDepth})`);
    const treeData = buildTree();
    console.log('构建的树数据:', treeData);
    
    if (treeData && dimensions) {
      const centerX = dimensions.width / 2;
      const centerY = dimensions.height / 2;
      // 减小基础半径，因为环间距增大了
      const baseRadius = Math.min(dimensions.width, dimensions.height) / 12;
      
      console.log('布局参数:', { centerX, centerY, baseRadius, dimensions });
      
      const positioned = calculateRadialLayout(treeData, centerX, centerY, baseRadius);
      console.log('布局后的树:', positioned);
      setTree(positioned);
    }
  }, [buildTree, calculateRadialLayout, dimensions, maxDisplayDepth]);

  // 5. 绘制函数
  const drawTree = useCallback(() => {
    if (!tree || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    // 设置Canvas分辨率
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    // 清空画布
    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    // 应用变换
    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(scale, scale);

    // 递归绘制连接线
    const drawConnections = (node) => {
      if (node.children) {
        node.children.forEach(child => {
          ctx.beginPath();
          ctx.strokeStyle = '#808080';
          ctx.lineWidth = 1.5;
          ctx.moveTo(node.x, node.y);
          ctx.lineTo(child.x, child.y);
          ctx.stroke();
          
          drawConnections(child);
        });
      }
    };

    // 递归绘制节点
    const drawNodes = (node) => {
      const isHovered = hoveredNode?.id === node.id;
      
      // 节点大小和颜色
      const sizes = [60, 45, 35, 25];
      const colors = ['#000080', '#008000', '#800080', '#c08000'];
      const size = sizes[node.level] || 20;
      const color = colors[node.level] || '#808080';

      if (node.level === 0) {
        // 根节点 - 方形
        const rectSize = size;
        ctx.fillStyle = isHovered ? '#ffffcc' : color;
        ctx.fillRect(node.x - rectSize, node.y - rectSize/2, rectSize * 2, rectSize);
        
        // Windows 98 边框
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.strokeRect(node.x - rectSize, node.y - rectSize/2, rectSize * 2, rectSize);
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        ctx.strokeRect(node.x - rectSize + 2, node.y - rectSize/2 + 2, rectSize * 2 - 4, rectSize - 4);
        
        // 文字
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 13px "MS Sans Serif", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // 文字截断
        let label = node.label;
        const maxWidth = rectSize * 2 - 10;
        while (ctx.measureText(label).width > maxWidth && label.length > 0) {
          label = label.slice(0, -1);
        }
        if (label !== node.label) label += '...';
        
        ctx.fillText(label, node.x, node.y);
      } else if (node.level === 3) {
        // 页码节点 - 小圆形
        ctx.fillStyle = isHovered ? '#ffffcc' : '#ffffff';
        ctx.beginPath();
        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
        ctx.fill();
        
        // 边框
        ctx.strokeStyle = '#808080';
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // 页码
        ctx.fillStyle = '#0000ff';
        ctx.font = 'bold 11px "MS Sans Serif", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.label, node.x, node.y);
      } else {
        // 其他节点 - 圆角矩形
        const rectWidth = size * 2.5;
        const rectHeight = size * 0.8;
        const radius = 4;
        
        ctx.fillStyle = isHovered ? '#ffffcc' : '#c0c0c0';
        
        // 绘制圆角矩形
        ctx.beginPath();
        ctx.moveTo(node.x - rectWidth/2 + radius, node.y - rectHeight/2);
        ctx.lineTo(node.x + rectWidth/2 - radius, node.y - rectHeight/2);
        ctx.arcTo(node.x + rectWidth/2, node.y - rectHeight/2, node.x + rectWidth/2, node.y - rectHeight/2 + radius, radius);
        ctx.lineTo(node.x + rectWidth/2, node.y + rectHeight/2 - radius);
        ctx.arcTo(node.x + rectWidth/2, node.y + rectHeight/2, node.x + rectWidth/2 - radius, node.y + rectHeight/2, radius);
        ctx.lineTo(node.x - rectWidth/2 + radius, node.y + rectHeight/2);
        ctx.arcTo(node.x - rectWidth/2, node.y + rectHeight/2, node.x - rectWidth/2, node.y + rectHeight/2 - radius, radius);
        ctx.lineTo(node.x - rectWidth/2, node.y - rectHeight/2 + radius);
        ctx.arcTo(node.x - rectWidth/2, node.y - rectHeight/2, node.x - rectWidth/2 + radius, node.y - rectHeight/2, radius);
        ctx.closePath();
        ctx.fill();
        
        // Windows 98 边框
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.strokeStyle = '#808080';
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // 文字
        ctx.fillStyle = '#000000';
        ctx.font = `${node.level === 1 ? 'bold ' : ''}11px "MS Sans Serif", sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // 文字截断
        let label = node.label;
        const maxWidth = rectWidth - 10;
        while (ctx.measureText(label).width > maxWidth && label.length > 0) {
          label = label.slice(0, -1);
        }
        if (label !== node.label) label += '...';
        
        ctx.fillText(label, node.x, node.y);
        
        // 页码范围标签
        if (node.pageRange) {
          ctx.font = '9px "MS Sans Serif", sans-serif';
          ctx.fillStyle = '#606060';
          const rangeText = `p.${node.pageRange[0]}-${node.pageRange[1]}`;
          ctx.fillText(rangeText, node.x, node.y + rectHeight/2 + 10);
        }
      }
      
      // 绘制子节点
      if (node.children) {
        node.children.forEach(drawNodes);
      }
    };

    drawConnections(tree);
    drawNodes(tree);

    ctx.restore();
  }, [tree, scale, hoveredNode, offset, dimensions]);

  // 6. 渲染
  useEffect(() => {
    drawTree();
  }, [drawTree]);

  // 6. 查找节点
  const findNodeAtPosition = useCallback((node, px, py) => {
    if (!node) return null;

    const sizes = [60, 45, 35, 25];
    const size = sizes[node.level] || 20;
    
    // 转换坐标
    const transformedX = (px - offset.x) / scale;
    const transformedY = (py - offset.y) / scale;
    
    const distance = Math.sqrt((node.x - transformedX) ** 2 + (node.y - transformedY) ** 2);
    
    if (distance <= size) {
      return node;
    }
    
    if (node.children) {
      for (const child of node.children) {
        const found = findNodeAtPosition(child, px, py);
        if (found) return found;
      }
    }
    
    return null;
  }, [offset, scale]);

  // 7. 事件处理
  const handleMouseMove = useCallback((e) => {
    if (isDragging) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      setOffset({ x: offset.x + dx, y: offset.y + dy });
      setDragStart({ x: e.clientX, y: e.clientY });
      return;
    }

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const node = findNodeAtPosition(tree, x, y);
    setHoveredNode(node);
    
    if (canvasRef.current) {
      canvasRef.current.style.cursor = node ? 'pointer' : 'default';
    }
  }, [tree, findNodeAtPosition, isDragging, dragStart, offset]);

  const handleMouseDown = useCallback((e) => {
    // 只响应中键（滚轮按下）
    if (e.button === 1) {
      e.preventDefault();
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      if (canvasRef.current) {
        canvasRef.current.style.cursor = 'grabbing';
      }
    }
  }, []);

  const handleMouseUp = useCallback((e) => {
    // 只处理中键释放
    if (e.button === 1) {
      setIsDragging(false);
      if (canvasRef.current) {
        canvasRef.current.style.cursor = hoveredNode ? 'pointer' : 'default';
      }
    }
  }, [hoveredNode]);

  const handleClick = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const node = findNodeAtPosition(tree, x, y);
    if (node) {
      if (node.page) {
        // 页码节点，直接跳转
        onPageClick?.(node.page);
      } else if (node.pageRange) {
        // 分段或细分节点，跳转到起始页
        onPageClick?.(node.pageRange[0]);
      }
    }
  }, [tree, findNodeAtPosition, onPageClick]);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    // 计算鼠标在画布坐标系中的位置（缩放前）
    const worldX = (mouseX - offset.x) / scale;
    const worldY = (mouseY - offset.y) / scale;
    
    // 缩放因子
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.3, Math.min(3, scale * delta));
    
    // 计算新的偏移量，使鼠标位置保持不变
    const newOffsetX = mouseX - worldX * newScale;
    const newOffsetY = mouseY - worldY * newScale;
    
    setScale(newScale);
    setOffset({ x: newOffsetX, y: newOffsetY });
  }, [scale, offset]);

  return (
    <div 
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#c0c0c0',
        border: '2px inset #ffffff',
        position: 'relative',
        overflow: 'hidden',
        fontFamily: 'MS Sans Serif, sans-serif'
      }}
    >
      {/* 控制面板 */}
      <div style={{
        position: 'absolute',
        top: 8,
        right: 8,
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        zIndex: 10
      }}>
        {/* 缩放控制 */}
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={() => setScale(s => Math.min(s * 1.2, 3))}
            style={{
              padding: '4px 8px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #ffffff',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif'
            }}
            onMouseDown={(e) => e.target.style.border = '2px inset #ffffff'}
            onMouseUp={(e) => e.target.style.border = '2px outset #ffffff'}
          >
            放大 +
          </button>
          <button
            onClick={() => setScale(s => Math.max(s * 0.8, 0.3))}
            style={{
              padding: '4px 8px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #ffffff',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif'
            }}
            onMouseDown={(e) => e.target.style.border = '2px inset #ffffff'}
            onMouseUp={(e) => e.target.style.border = '2px outset #ffffff'}
          >
            缩小 -
          </button>
          <button
            onClick={() => {
              setScale(1);
              setOffset({ x: 0, y: 0 });
            }}
            style={{
              padding: '4px 8px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #ffffff',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif'
            }}
            onMouseDown={(e) => e.target.style.border = '2px inset #ffffff'}
            onMouseUp={(e) => e.target.style.border = '2px outset #ffffff'}
          >
            重置
          </button>
        </div>

        {/* 层级控制 */}
        <div style={{
          backgroundColor: '#c0c0c0',
          border: '2px outset #ffffff',
          padding: '6px 8px'
        }}>
          <div style={{
            fontSize: '11px',
            marginBottom: 4,
            fontWeight: 'bold',
            color: '#000080'
          }}>
            显示层级：
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {[
              { depth: 1, label: '🔵 文件 + 分段' },
              { depth: 2, label: '🔵🟢 + 细分' },
              { depth: 3, label: '🔵🟢🟣 + 页码' }
            ].map(({ depth, label }) => (
              <button
                key={depth}
                onClick={() => {
                  setMaxDisplayDepth(depth);
                  setScale(1);
                  setOffset({ x: 0, y: 0 });
                }}
                style={{
                  padding: '3px 6px',
                  fontSize: '10px',
                  backgroundColor: maxDisplayDepth === depth ? '#000080' : '#c0c0c0',
                  color: maxDisplayDepth === depth ? '#ffffff' : '#000000',
                  border: maxDisplayDepth === depth ? '2px inset #ffffff' : '2px outset #ffffff',
                  cursor: 'pointer',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  textAlign: 'left'
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 提示文字 */}
      {hoveredNode && (
        <div style={{
          position: 'absolute',
          bottom: 8,
          left: 8,
          backgroundColor: '#ffffcc',
          border: '1px solid #000000',
          padding: '4px 8px',
          fontSize: '11px',
          maxWidth: '300px',
          wordWrap: 'break-word'
        }}>
          <strong>{hoveredNode.label}</strong>
          {hoveredNode.pageRange && (
            <div style={{ fontSize: '10px', color: '#606060' }}>
              页码: {hoveredNode.pageRange[0]}-{hoveredNode.pageRange[1]}
            </div>
          )}
          {hoveredNode.page && (
            <div style={{ fontSize: '10px', color: '#0000ff' }}>
              点击跳转到第 {hoveredNode.page} 页
            </div>
          )}
        </div>
      )}

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block'
        }}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
        onWheel={handleWheel}
      />
    </div>
  );
};

export default RadialMindMap;

