from plugins.base import MangaPluginBase, Formats, AgeRating, NO_THUMBNAIL_URL
import sys
import requests
import json
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class MangaDex(MangaPluginBase):
    languages = ["en","pt","pt-br","it","de","ru","aa","ab","ae","af","ak","am","an","ar-ae","ar-bh","ar-dz","ar-eg","ar-iq","ar-jo","ar-kw","ar-lb","ar-ly","ar-ma","ar-om","ar-qa","ar-sa","ar-sy","ar-tn","ar-ye","ar","as","av","ay","az","ba","be","bg","bh","bi","bm","bn","bo","br","bs","ca","ce","ch","co","cr","cs","cu","cv","cy","da","de-at","de-ch","de-de","de-li","de-lu","div","dv","dz","ee","el","en-au","en-bz","en-ca","en-cb","en-gb","en-ie","en-jm","en-nz","en-ph","en-tt","en-us","en-za","en-zw","eo","es-ar","es-bo","es-cl","es-co","es-cr","es-do","es-ec","es-es","es-gt","es-hn","es-la","es-mx","es-ni","es-pa","es-pe","es-pr","es-py","es-sv","es-us","es-uy","es-ve","es","et","eu","fa","ff","fi","fj","fo","fr-be","fr-ca","fr-ch","fr-fr","fr-lu","fr-mc","fr","fy","ga","gd","gl","gn","gu","gv","ha","he","hi","ho","hr-ba","hr-hr","hr","ht","hu","hy","hz","ia","id","ie","ig","ii","ik","in","io","is","it-ch","it-it","iu","iw","ja","ja-ro","ji","jv","jw","ka","kg","ki","kj","kk","kl","km","kn","ko","ko-ro","kr","ks","ku","kv","kw","ky","kz","la","lb","lg","li","ln","lo","ls","lt","lu","lv","mg","mh","mi","mk","ml","mn","mo","mr","ms-bn","ms-my","ms","mt","my","na","nb","nd","ne","ng","nl-be","nl-nl","nl","nn","no","nr","ns","nv","ny","oc","oj","om","or","os","pa","pi","pl","ps","pt-pt","qu-bo","qu-ec","qu-pe","qu","rm","rn","ro","rw","sa","sb","sc","sd","se-fi","se-no","se-se","se","sg","sh","si","sk","sl","sm","sn","so","sq","sr-ba","sr-sp","sr","ss","st","su","sv-fi","sv-se","sv","sw","sx","syr","ta","te","tg","th","ti","tk","tl","tn","to","tr","ts","tt","tw","ty","ug","uk","ur","us","uz","ve","vi","vo","wa","wo","xh","yi","yo","za","zh-cn","zh-hk","zh-mo","zh-ro","zh-sg","zh-tw","zh","zu"]
    base_url = "https://mangadex.org"
    api_url = f"https://api.mangadex.org"

    def search_manga(self, query, language=None):
        logger.debug(f'Searching for "{query}"')
        limit = 100
        offset = 0
        total = sys.maxsize

        mangaData = []
        while offset < total:
            try:
                response = requests.get(f'{self.api_url}/manga',
                                        params={
                                            "title": query,
                                            "limit": limit,
                                            "offset": offset,
                                            "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"] if self.nsfw_allowed else ["safe"],
                                            "includes[]": ["manga", "cover_art", "author", "artist", "tag"],
                                        },
                                        timeout=10
                                        )
                response.raise_for_status()

                result = response.json()

                offset += limit
                if result is None:
                    break

                if "total" in result:
                    total = int(result.get("total"))
                else:
                    continue

                if "data" in result:
                    result_datas = result.get("data")
                    for result_data in result_datas:
                        manga_dict = self.search_manga_dict()
                        attributes = result_data.get("attributes", {})
                        manga_dict["language"]= language
                        titles = attributes.get("title", {})
                        if language is None:
                            for key, value in titles.items():
                                if manga_dict["language"] is None:
                                    manga_dict["language"]= key
                                manga_dict["name"] = value
                                break
                        else:
                            manga_dict["name"] = titles.get(language)
                        if manga_dict["name"] is None:
                            continue
                        
                        descriptions = attributes.get("description", {})
                        manga_dict["description"] = descriptions.get(language)
                        if manga_dict["description"] is None:
                            for key, value in descriptions.items():
                                manga_dict["description"] = value
                                break
                        
                        tags = attributes.get("tags", [])
                        manga_dict["genres"] = []
                        manga_dict["tags"] = []
                        for tag in tags:
                            tag_attributes = tag.get("attributes", {})
                            tag_group = tag_attributes.get("group")
                            if tag_group is not None and tag_group == "genre":
                                tag_names = tag_attributes.get("name")
                                tag_name = tag_names.get(language)
                                if tag_name is None:
                                    for key, value in tag_names.items():
                                        manga_dict["genres"].append(value)
                                        break
                                else:
                                    manga_dict["genres"].append(tag_name)
                            if tag_group is not None and tag_group == "theme":
                                tag_names = tag_attributes.get("name")
                                tag_name = tag_names.get(language)
                                if tag_name is None:
                                    for key, value in tag_names.items():
                                        manga_dict["tags"].append(value)
                                        break
                                else:
                                    manga_dict["tags"].append(tag_name)

                        status = attributes.get("status")
                        manga_dict["complete"] = False
                        if status == "completed" or status == "cancelled":
                            manga_dict["complete"] = True
                        

                        id = result_data.get("id")
                        cover_url = NO_THUMBNAIL_URL
                        if id is not None:
                            manga_dict["id"] = id
                            manga_dict["url"] = f"{self.base_url}/title/{id}"
                            relationships = result_data.get("relationships")
                            if relationships is not None:
                                for relationship in relationships:
                                    if relationship.get("type") == "cover_art":
                                        cover_fileName = relationship.get("attributes", {}).get("fileName")
                                        if relationships is not None:
                                            cover_url = f"https://uploads.mangadex.org/covers/{id}/{cover_fileName}.256.jpg"
                                        break

                            manga_dict["cover"] = cover_url
                            mangaData.append(manga_dict)
            except Exception as e:
                logger.error(f'Error while searching manga - {e}')
                break

        return mangaData
    
    @staticmethod
    def get_lang_value(s, lang, default=None):
        value = s.get(lang)
        if value is None:
            for k, v in s.items():
                return v
        return value or default

    def get_manga(self, arguments):
        manga = self.get_manga_dict()
        try:
            id = arguments.get("id")
            if id is None:
                raise Exception("There is no ID in arguments")
            response = requests.get(f'{self.api_url}/manga/{id}',
                                    params={
                                        "includes[]": ["manga", "cover_art", "author", "artist", "tag"],
                                    },
                                    timeout=10
                                    )
            response.raise_for_status()

            manga["id"] = id
            result = response.json()

            data = result.get("data")
            attributes = data.get("attributes", {})
            language = arguments.get("language")

            titles = attributes.get("title", {})
            manga["name"] = self.get_lang_value(titles, language, arguments.get("name"))

            alt_titles = attributes.get("altTitles", [])
            for alt_title in alt_titles:
                alt_title_l = self.get_lang_value(alt_title, language)
                if alt_title_l is None:
                    continue
                manga["alt_names"].append(alt_title_l)

            descriptions = attributes.get("description", {})
            manga["description"] = self.get_lang_value(descriptions, language, arguments.get("description"))

            manga["original_language"] = attributes.get("originalLanguage", language or "un")


            tags = attributes.get("tags", [])
            manga["genres"] = []
            manga["tags"] = []
            for tag in tags:
                tag_attributes = tag.get("attributes", {})
                tag_group = tag_attributes.get("group")
                if tag_group is not None and tag_group == "genre":
                    tag_names = tag_attributes.get("name")
                    tag_name = self.get_lang_value(tag_names, language)
                    if tag_name is None:
                        continue
                    manga["genres"].append(tag_name)
                if tag_group is not None and tag_group == "theme":
                    tag_names = tag_attributes.get("name")
                    tag_name = self.get_lang_value(tag_names, language)
                    if tag_name is None:
                        continue
                    manga["tags"].append(tag_name)

                    
            status = attributes.get("status")
            manga["complete"] = False
            if status == "completed" or status == "cancelled":
                manga["complete"] = True

            manga["url"] = arguments.get("url")
            manga["language"] = arguments.get("language")
        except Exception as e:
            logger.error(f'Error while getting manga - {e}')

        return manga
    
    def get_volumes(self, arguments):
        return []
    
    def get_chapters(self, arguments):
        logger.debug(f'Searching for chapters')
        limit = 100
        offset = 0
        total = sys.maxsize

        chapterData = []
        while offset < total:
            try:
                id = arguments.get("id")
                if id is None:
                    raise Exception("There is no ID in arguments")
                language = arguments.get("language")
                if language is None:
                    raise Exception("There is no language in arguments")
                response = requests.get(f'{self.api_url}/manga/{id}/feed',
                                        params={
                                            "limit": limit,
                                            "offset": offset,
                                            "translatedLanguage[]": language,
                                            "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"] if self.nsfw_allowed else ["safe"],
                                            "includes[]": ["manga", "cover_art", "author", "artist", "tag"],
                                        },
                                        timeout=10
                                        )
                response.raise_for_status()

                result = response.json()

                offset += limit

                if result is None:
                    break

                total = result.get("total")

                datas = result.get("data")

                for data in datas:
                    chapter_id = data.get("id")
                    if chapter_id is None:
                        continue

                    chapter = self.get_chapter_dict()
                    attributes = data.get("attributes", {})

                    chapter["name"] = attributes.get("title") or arguments.get("name")
                    chapter["localization"] = attributes.get("translatedLanguage")
                    chapter_number = attributes.get("chapter")
                    if chapter_number != "None" and chapter_number is not None:
                        chapter["chapter_number"] = chapter_number
                    volume_number = attributes.get("volume")
                    if volume_number != "None" and volume_number is not None:
                        chapter["volume_number"] = volume_number
                    chapter["release_date"] = datetime.strptime(attributes.get("publishAt"), "%Y-%m-%dT%H:%M:%S%z")
                    chapter["page_count"] = attributes.get("pages")
                    chapter["source_url"] = f'{self.base_url}/chapter/{chapter_id}'
                    chapter["url"] = f'{self.api_url}/at-home/server/{chapter_id}?forcePort443=false'

                    chapterData.append(chapter)

            except Exception as e:
                logger.error(f'Error while getting chapters - {e}')
                break


        return chapterData
    
    def get_pages(self, arguments):
        logger.debug(f'Searching for pages')
        pagesData = []
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            result = response.json()

            base_url = result.get("baseUrl")
            if base_url is None:
                return pagesData
            
            chapter = result.get("chapter", {})

            chapter_hash = chapter.get("hash")
            if chapter_hash is None:
                return pagesData
            
            page_base_url = f'{base_url}/data/{chapter_hash}'

            for page_file in chapter.get("data", []):
                page = self.get_page_dict()
                page["url"] = f'{page_base_url}/{page_file}'
                pagesData.append(page)

        except Exception as e:
            logger.error(f'Error while getting pages - {e}')

        return pagesData