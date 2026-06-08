import type { GroupSpec } from "../types";
import { consumption } from "./consumption";
import { supply } from "./supply";
import { inflation } from "./inflation";
import { rates } from "./rates";
import { sentiment } from "./sentiment";
import { breadth } from "./breadth";

/** 六组 21 张图(20 张主题图 + F&G) */
export const GROUPS: GroupSpec[] = [sentiment, rates, breadth, inflation, consumption, supply];
