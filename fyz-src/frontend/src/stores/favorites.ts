import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { dataProvider } from "@/data";
import type { FavoriteRecord, FavoriteTargetType } from "@/domain/types";

export const useFavoriteStore=defineStore("favorites",()=>{
  const records=ref<FavoriteRecord[]>([]),loading=ref(false),loaded=ref(false),error=ref("");
  async function load(force=false){if(loaded.value&&!force)return;loading.value=true;error.value="";try{records.value=await dataProvider.favorites.list();loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  const keys=computed(()=>new Set(records.value.map(v=>`${v.target_type}:${v.target_id}`)));
  const isFavorite=(type:FavoriteTargetType,id:number)=>keys.value.has(`${type}:${id}`);
  async function toggle(type:FavoriteTargetType,id:number,title?:string){const active=await dataProvider.favorites.toggle(type,id,title);records.value=await dataProvider.favorites.list();loaded.value=true;return active;}
  async function removeMany(ids:number[]){await dataProvider.favorites.removeMany(ids);records.value=records.value.filter(v=>!ids.includes(v.id));}
  async function updateNote(id:number,note:string){await dataProvider.favorites.updateNote(id,note);const item=records.value.find(v=>v.id===id);if(item)item.note=note;}
  return {records,loading,loaded,error,load,refresh:()=>load(true),isFavorite,toggle,removeMany,updateNote};
});
