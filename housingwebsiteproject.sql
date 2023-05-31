-- phpMyAdmin SQL Dump
-- version 5.1.1
-- https://www.phpmyadmin.net/
--
-- 主機： 127.0.0.1
-- 產生時間： 2023-05-31 04:44:33
-- 伺服器版本： 10.4.22-MariaDB
-- PHP 版本： 8.1.2

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 資料庫: `housingwebsiteproject`
--

-- --------------------------------------------------------

--
-- 資料表結構 `browses`
--

CREATE TABLE `browses` (
  `uId` int(10) NOT NULL,
  `pId` int(10) NOT NULL,
  `browseTime` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `criticizes`
--

CREATE TABLE `criticizes` (
  `cId` int(10) NOT NULL,
  `uId` int(10) NOT NULL,
  `pId` int(10) NOT NULL,
  `comment` text NOT NULL,
  `reviseDateTime` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `house`
--

CREATE TABLE `house` (
  `hId` int(10) NOT NULL,
  `type` enum('住宅','獨立套房','分租套房','雅房') DEFAULT NULL,
  `twPing` float DEFAULT NULL,
  `floor` varchar(10) NOT NULL,
  `lived` tinyint(1) NOT NULL,
  `bedRoom` int(2) DEFAULT NULL,
  `livingRoom` int(2) DEFAULT NULL,
  `restRoom` int(2) DEFAULT NULL,
  `balcony` int(2) DEFAULT NULL,
  `pId` int(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `houserent`
--

CREATE TABLE `houserent` (
  `hId` int(11) NOT NULL,
  `price` int(10) NOT NULL,
  `refrigerator` tinyint(1) NOT NULL,
  `washingMachine` tinyint(1) NOT NULL,
  `TV` tinyint(1) NOT NULL,
  `airConditioner` tinyint(1) NOT NULL,
  `waterHeater` tinyint(1) NOT NULL,
  `bed` tinyint(1) NOT NULL,
  `closet` tinyint(1) NOT NULL,
  `paidTVChannel` tinyint(1) NOT NULL,
  `internet` tinyint(1) NOT NULL,
  `gas` tinyint(1) NOT NULL,
  `sofa` tinyint(1) NOT NULL,
  `deskChair` tinyint(1) NOT NULL,
  `balcony` tinyint(1) NOT NULL,
  `elevator` tinyint(1) NOT NULL,
  `parkingSpace` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `housesell`
--

CREATE TABLE `housesell` (
  `hId` int(11) NOT NULL,
  `ratioOfPublicArea` float DEFAULT NULL,
  `pricePerTwping` float NOT NULL,
  `price` float NOT NULL,
  `age` int(3) NOT NULL,
  `houseType` enum('華廈','電梯大樓','公寓','透天厝','別墅') NOT NULL,
  `houseName` varchar(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `image`
--

CREATE TABLE `image` (
  `pId` int(10) NOT NULL,
  `image` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `payment`
--

CREATE TABLE `payment` (
  `pId` int(11) NOT NULL,
  `payDate` date NOT NULL,
  `endDate` date NOT NULL,
  `class` tinyint(1) NOT NULL,
  `expDate` date NOT NULL,
  `cardNumber` text NOT NULL,
  `cost` int(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `post`
--

CREATE TABLE `post` (
  `pId` int(10) NOT NULL,
  `uId` int(10) NOT NULL,
  `title` text NOT NULL,
  `city` varchar(10) NOT NULL,
  `district` varchar(10) NOT NULL,
  `address` varchar(10) NOT NULL,
  `name` varchar(10) NOT NULL,
  `phone` varchar(10) NOT NULL,
  `description` text NOT NULL,
  `reviseDateTime` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 資料表結構 `user`
--

CREATE TABLE `user` (
  `uId` int(10) NOT NULL,
  `name` varchar(10) NOT NULL,
  `phone` text NOT NULL DEFAULT '0912345678',
  `email` varchar(40) NOT NULL,
  `password` varchar(20) NOT NULL,
  `permission` enum('user','manager') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 已傾印資料表的索引
--

--
-- 資料表索引 `browses`
--
ALTER TABLE `browses`
  ADD PRIMARY KEY (`uId`,`pId`,`browseTime`);

--
-- 資料表索引 `criticizes`
--
ALTER TABLE `criticizes`
  ADD PRIMARY KEY (`cId`);

--
-- 資料表索引 `house`
--
ALTER TABLE `house`
  ADD PRIMARY KEY (`hId`);

--
-- 資料表索引 `payment`
--
ALTER TABLE `payment`
  ADD PRIMARY KEY (`pId`,`payDate`);

--
-- 資料表索引 `post`
--
ALTER TABLE `post`
  ADD PRIMARY KEY (`pId`);

--
-- 資料表索引 `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`uId`);

--
-- 在傾印的資料表使用自動遞增(AUTO_INCREMENT)
--

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `house`
--
ALTER TABLE `house`
  MODIFY `hId` int(10) NOT NULL AUTO_INCREMENT;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `user`
--
ALTER TABLE `user`
  MODIFY `uId` int(10) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
