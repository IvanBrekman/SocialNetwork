function getCookie(name) {
    let matches = document.cookie.match(new RegExp(
        "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
    ));
    return matches ? decodeURIComponent(matches[1]) : undefined;
}

function setCookie(name, value, options = {}) {

    options = {
        path: '/',
        // при необходимости добавьте другие значения по умолчанию
        ...options
    };

    if (options.expires instanceof Date) {
        options.expires = options.expires.toUTCString();
    }

    let updatedCookie = encodeURIComponent(name) + "=" + encodeURIComponent(value);

    for (let optionKey in options) {
        updatedCookie += "; " + optionKey;
        let optionValue = options[optionKey];
        if (optionValue !== true) {
            updatedCookie += "=" + optionValue;
        }
    }

    document.cookie = updatedCookie;
}

function oppositeColor(color) {
    if (color === "white")
        return {background: "#1f1b42", form: "#4b39af", labels: "white"}
    return {background: "white", form: "white", labels:"black"}
}

function fillPage(col){
    document.getElementsByTagName("body")[0].style.background = col
    let hhes=document.getElementsByTagName("h1")
        for(let i=0; i<hhes.length; i++){
            hhes[i].style.color = oppositeColor(col).background
        }
        let cards=document.getElementsByClassName("card")
        let labels=document.getElementsByTagName("label")
        console.log(col)
        console.log(oppositeColor(oppositeColor(col).background).form)
        for (let i = 0; i < cards.length; i++) {
            cards[i].style.background = oppositeColor(oppositeColor(col).background).form
        }
        for (let i = 0; i < labels.length; i++) {
            labels[i].style.color = oppositeColor(oppositeColor(col).background).labels
        }
}

switchTheme.onclick = () => {
    let body = document.getElementsByTagName("body")
    let cur_color = body[0].style.background
    fillPage(oppositeColor(cur_color).background)
    setCookie("color", oppositeColor(cur_color).background)  //сохраняем текущий state в куки, для дальнейшего использования на др страницах.
}

function setTheme() {
    try {
        let col = getCookie("color")
        if (col)
            fillPage(col)
        else
            fillPage("white")

    }
    catch (e) {
        console.error(e)
    }
}

setTheme()
