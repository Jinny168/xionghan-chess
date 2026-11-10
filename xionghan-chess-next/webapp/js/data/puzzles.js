/** 训练题库：9 道走法教学 + 12 道引擎生成的一步杀（均经规则引擎验证）。 */
export const PUZZLES = [
 {
  "id": "beginner-forward-01",
  "title": "兵卒初动",
  "level": "beginner",
  "desc": "熟悉匈汉棋盘上兵的前进方向。",
  "profileId": "web",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 8,
     "col": 0
    },
    "to": {
     "row": 7,
     "col": 0
    },
    "promotion": null
   }
  ],
  "hints": [
   "观察红方最左侧的兵。",
   "红方向行号减小的方向前进。"
  ]
 },
 {
  "id": "beginner-cannon-01",
  "title": "架炮出营",
  "level": "beginner",
  "desc": "找到炮在无阻挡直线上的安全展开点。",
  "profileId": "traditional",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 7,
     "col": 1
    },
    "to": {
     "row": 6,
     "col": 1
    },
    "promotion": null
   }
  ],
  "hints": [
   "炮不吃子时沿直线移动。",
   "向前移动一格即可。"
  ]
 },
 {
  "id": "beginner-horse-01",
  "title": "跃马争先",
  "level": "beginner",
  "desc": "练习马的日字移动与蹩马腿判断。",
  "profileId": "traditional",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 9,
     "col": 1
    },
    "to": {
     "row": 7,
     "col": 2
    },
    "promotion": null
   }
  ],
  "hints": [
   "先检查马腿位置是否为空。",
   "目标位于右前方日字落点。"
  ]
 },
 {
  "id": "advanced-archer-01",
  "title": "星轨射手",
  "level": "advanced",
  "desc": "识别射在弱化模式下可进入的相邻星轨。",
  "profileId": "web",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 12,
     "col": 0
    },
    "to": {
     "row": 9,
     "col": 3
    },
    "promotion": null
   }
  ],
  "hints": [
   "射只能沿有效星轨移动。",
   "从角部星点沿右上轨道前进。"
  ]
 },
 {
  "id": "advanced-patrol-01",
  "title": "巡守河界",
  "level": "advanced",
  "desc": "掌握巡在指定边界上的横向调动。",
  "profileId": "desktop_classic",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 7,
     "col": 0
    },
    "to": {
     "row": 7,
     "col": 2
    },
    "promotion": null
   }
  ],
  "hints": [
   "找到红方位于边界线的巡。",
   "沿边界横移两个交点。"
  ]
 },
 {
  "id": "advanced-center-01",
  "title": "中兵抢渡",
  "level": "advanced",
  "desc": "用中路兵争夺长城阴山区域。",
  "profileId": "desktop_complete",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 8,
     "col": 6
    },
    "to": {
     "row": 7,
     "col": 6
    },
    "promotion": null
   }
  ],
  "hints": [
   "关注中线兵。",
   "先控制边界入口。"
  ]
 },
 {
  "id": "master-thunder-01",
  "title": "檑动中军",
  "level": "master",
  "desc": "规划檑从底线向中路展开的第一步。",
  "profileId": "desktop_complete",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 12,
     "col": 4
    },
    "to": {
     "row": 12,
     "col": 5
    },
    "promotion": null
   }
  ],
  "hints": [
   "檑可以沿直线或斜线移动。",
   "先沿底线靠近中军。"
  ]
 },
 {
  "id": "master-guard-01",
  "title": "尉卫跳阵",
  "level": "master",
  "desc": "理解尉卫隔子跳跃的起跳条件。",
  "profileId": "desktop_complete",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 12,
     "col": 6
    },
    "to": {
     "row": 10,
     "col": 6
    },
    "promotion": null
   }
  ],
  "hints": [
   "尉需要隔一枚棋子起跳。",
   "观察正前方的主帅与后续落点。"
  ]
 },
 {
  "id": "master-rook-01",
  "title": "俥占要道",
  "level": "master",
  "desc": "在完整棋阵中寻找俥的可用直线。",
  "profileId": "desktop_complete",
  "type": "move",
  "start": "initial",
  "solution": [
   {
    "from": {
     "row": 11,
     "col": 2
    },
    "to": {
     "row": 10,
     "col": 2
    },
    "promotion": null
   }
  ],
  "hints": [
   "俥不能越子。",
   "向前一格是当前最直接的展开点。"
  ]
 },
 {
  "id": "mate-rook-1",
  "title": "俥压九宫",
  "level": "tactics",
  "desc": "用车一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 9,
    "col": 8
   },
   {
    "type": "king",
    "color": "black",
    "row": 4,
    "col": 4
   },
   {
    "type": "rook",
    "color": "black",
    "row": 9,
    "col": 7
   },
   {
    "type": "horse",
    "color": "black",
    "row": 7,
    "col": 11
   },
   {
    "type": "advisor",
    "color": "red",
    "row": 11,
    "col": 8
   }
  ],
  "solution": [
   {
    "from": {
     "row": 9,
     "col": 7
    },
    "to": {
     "row": 9,
     "col": 8
    },
    "promotion": null
   },
   {
    "from": {
     "row": 7,
     "col": 11
    },
    "to": {
     "row": 9,
     "col": 10
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意rook的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-rook-2",
  "title": "俥压九宫 · 其二",
  "level": "tactics",
  "desc": "用车一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 8,
    "col": 9
   },
   {
    "type": "king",
    "color": "black",
    "row": 1,
    "col": 8
   },
   {
    "type": "horse",
    "color": "black",
    "row": 10,
    "col": 4
   },
   {
    "type": "rook",
    "color": "black",
    "row": 12,
    "col": 9
   },
   {
    "type": "armor",
    "color": "black",
    "row": 10,
    "col": 10
   }
  ],
  "solution": [
   {
    "from": {
     "row": 12,
     "col": 9
    },
    "to": {
     "row": 8,
     "col": 9
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意rook的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-cannon-3",
  "title": "重炮锁宫",
  "level": "tactics",
  "desc": "用炮一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 11,
    "col": 4
   },
   {
    "type": "king",
    "color": "black",
    "row": 2,
    "col": 6
   },
   {
    "type": "cannon",
    "color": "black",
    "row": 11,
    "col": 8
   },
   {
    "type": "guard",
    "color": "black",
    "row": 11,
    "col": 6
   },
   {
    "type": "armor",
    "color": "red",
    "row": 8,
    "col": 9
   },
   {
    "type": "shield",
    "color": "red",
    "row": 7,
    "col": 4
   }
  ],
  "solution": [
   {
    "from": {
     "row": 11,
     "col": 8
    },
    "to": {
     "row": 11,
     "col": 4
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意cannon的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-pawn-4",
  "title": "兵临城下",
  "level": "tactics",
  "desc": "用兵一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 10,
    "col": 8
   },
   {
    "type": "king",
    "color": "black",
    "row": 4,
    "col": 9
   },
   {
    "type": "pawn",
    "color": "black",
    "row": 10,
    "col": 9
   },
   {
    "type": "assassin",
    "color": "black",
    "row": 8,
    "col": 1
   },
   {
    "type": "guard",
    "color": "red",
    "row": 8,
    "col": 2
   }
  ],
  "solution": [
   {
    "from": {
     "row": 10,
     "col": 9
    },
    "to": {
     "row": 10,
     "col": 8
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意pawn的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-horse-5",
  "title": "卧槽绝杀",
  "level": "tactics",
  "desc": "用马一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 11,
    "col": 6
   },
   {
    "type": "king",
    "color": "black",
    "row": 1,
    "col": 6
   },
   {
    "type": "horse",
    "color": "black",
    "row": 10,
    "col": 8
   },
   {
    "type": "armor",
    "color": "black",
    "row": 9,
    "col": 12
   },
   {
    "type": "rook",
    "color": "black",
    "row": 9,
    "col": 11
   },
   {
    "type": "pawn",
    "color": "red",
    "row": 7,
    "col": 6
   }
  ],
  "solution": [
   {
    "from": {
     "row": 10,
     "col": 8
    },
    "to": {
     "row": 11,
     "col": 6
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意horse的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-thunder-6",
  "title": "檑震中军",
  "level": "tactics",
  "desc": "用檑一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 10,
    "col": 5
   },
   {
    "type": "king",
    "color": "black",
    "row": 1,
    "col": 7
   },
   {
    "type": "thunder",
    "color": "black",
    "row": 11,
    "col": 4
   },
   {
    "type": "rook",
    "color": "black",
    "row": 10,
    "col": 2
   },
   {
    "type": "guard",
    "color": "black",
    "row": 9,
    "col": 5
   },
   {
    "type": "advisor",
    "color": "black",
    "row": 10,
    "col": 10
   },
   {
    "type": "pawn",
    "color": "red",
    "row": 12,
    "col": 8
   }
  ],
  "solution": [
   {
    "from": {
     "row": 11,
     "col": 4
    },
    "to": {
     "row": 10,
     "col": 5
    },
    "promotion": null
   },
   {
    "from": {
     "row": 10,
     "col": 2
    },
    "to": {
     "row": 10,
     "col": 5
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意thunder的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-advisor-7",
  "title": "仕角抽将",
  "level": "tactics",
  "desc": "用仕一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "red",
  "pieces": [
   {
    "type": "king",
    "color": "black",
    "row": 0,
    "col": 6
   },
   {
    "type": "king",
    "color": "red",
    "row": 10,
    "col": 3
   },
   {
    "type": "advisor",
    "color": "red",
    "row": 1,
    "col": 5
   },
   {
    "type": "cannon",
    "color": "red",
    "row": 6,
    "col": 11
   }
  ],
  "solution": [
   {
    "from": {
     "row": 1,
     "col": 5
    },
    "to": {
     "row": 0,
     "col": 6
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意advisor的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-armor-8",
  "title": "甲胄合击",
  "level": "tactics",
  "desc": "用甲一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 10,
    "col": 8
   },
   {
    "type": "king",
    "color": "black",
    "row": 1,
    "col": 4
   },
   {
    "type": "advisor",
    "color": "black",
    "row": 12,
    "col": 8
   },
   {
    "type": "armor",
    "color": "black",
    "row": 11,
    "col": 12
   },
   {
    "type": "cannon",
    "color": "black",
    "row": 8,
    "col": 7
   },
   {
    "type": "elephant",
    "color": "black",
    "row": 10,
    "col": 12
   },
   {
    "type": "advisor",
    "color": "red",
    "row": 12,
    "col": 5
   }
  ],
  "solution": [
   {
    "from": {
     "row": 11,
     "col": 12
    },
    "to": {
     "row": 11,
     "col": 8
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意armor的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-archer-9",
  "title": "星轨封喉",
  "level": "tactics",
  "desc": "用射一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "red",
  "pieces": [
   {
    "type": "king",
    "color": "black",
    "row": 1,
    "col": 7
   },
   {
    "type": "king",
    "color": "red",
    "row": 11,
    "col": 9
   },
   {
    "type": "horse",
    "color": "red",
    "row": 6,
    "col": 10
   },
   {
    "type": "archer",
    "color": "red",
    "row": 2,
    "col": 8
   },
   {
    "type": "pawn",
    "color": "red",
    "row": 1,
    "col": 2
   },
   {
    "type": "rook",
    "color": "red",
    "row": 6,
    "col": 1
   }
  ],
  "solution": [
   {
    "from": {
     "row": 2,
     "col": 8
    },
    "to": {
     "row": 1,
     "col": 7
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意archer的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-armor-10",
  "title": "甲胄合击 · 其二",
  "level": "tactics",
  "desc": "用甲一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 10,
    "col": 3
   },
   {
    "type": "king",
    "color": "black",
    "row": 1,
    "col": 8
   },
   {
    "type": "cannon",
    "color": "black",
    "row": 11,
    "col": 3
   },
   {
    "type": "advisor",
    "color": "black",
    "row": 11,
    "col": 9
   },
   {
    "type": "armor",
    "color": "black",
    "row": 9,
    "col": 7
   },
   {
    "type": "horse",
    "color": "black",
    "row": 11,
    "col": 1
   }
  ],
  "solution": [
   {
    "from": {
     "row": 9,
     "col": 7
    },
    "to": {
     "row": 9,
     "col": 3
    },
    "promotion": null
   },
   {
    "from": {
     "row": 11,
     "col": 1
    },
    "to": {
     "row": 10,
     "col": 3
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意armor的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-horse-11",
  "title": "卧槽绝杀 · 其二",
  "level": "tactics",
  "desc": "用马一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "red",
  "pieces": [
   {
    "type": "king",
    "color": "black",
    "row": 4,
    "col": 4
   },
   {
    "type": "king",
    "color": "red",
    "row": 12,
    "col": 3
   },
   {
    "type": "horse",
    "color": "red",
    "row": 3,
    "col": 6
   },
   {
    "type": "rook",
    "color": "red",
    "row": 6,
    "col": 5
   },
   {
    "type": "archer",
    "color": "red",
    "row": 0,
    "col": 5
   },
   {
    "type": "guard",
    "color": "black",
    "row": 2,
    "col": 4
   }
  ],
  "solution": [
   {
    "from": {
     "row": 3,
     "col": 6
    },
    "to": {
     "row": 4,
     "col": 4
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意horse的杀法，目标是把对方主帅困死。"
  ]
 },
 {
  "id": "mate-assassin-12",
  "title": "刺客同归",
  "level": "tactics",
  "desc": "用刺一步将死。",
  "profileId": "desktop_complete",
  "type": "mate",
  "turn": "black",
  "pieces": [
   {
    "type": "king",
    "color": "red",
    "row": 8,
    "col": 7
   },
   {
    "type": "king",
    "color": "black",
    "row": 0,
    "col": 4
   },
   {
    "type": "assassin",
    "color": "black",
    "row": 8,
    "col": 9
   },
   {
    "type": "horse",
    "color": "black",
    "row": 10,
    "col": 12
   }
  ],
  "solution": [
   {
    "from": {
     "row": 8,
     "col": 9
    },
    "to": {
     "row": 8,
     "col": 11
    },
    "promotion": null
   }
  ],
  "hints": [
   "注意assassin的杀法，目标是把对方主帅困死。"
  ]
 }
];
